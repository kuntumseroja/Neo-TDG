"""Thorough integration test for the knowledge store + ingestion pipeline.

Exercises every path the UI uses:
  1. Empty store → stats consistency
  2. Single doc ingest → chunks + stats grow
  3. Same doc_id re-ingest → chunks REPLACED (no growth)
  4. Different doc_id ingest → chunks ADDED (growth)
  5. Query retrieval with and without filters
  6. Delete → chunks + stats shrink
  7. Pipeline.ingest_markdown_file (path-hash doc_id)
  8. Pipeline.ingest_markdown_directory
  9. Pipeline.ingest_crawl_report with deterministic per-service doc_ids
 10. Upload-tab md5(name:size) doc_id pattern
 11. Unicode / special chars / empty-doc edge cases
 12. get_all_doc_ids consistency
 13. Rebuild index

Run with: python3 tests/test_knowledge_integration.py
"""

from __future__ import annotations

import hashlib
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

# Make src/ importable when run as a script.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.knowledge.vector_store import VectorKnowledgeStore  # noqa: E402
from src.knowledge.embeddings import BaseEmbeddingProvider  # noqa: E402
from src.pipeline.ingestion import DocumentIngestionPipeline  # noqa: E402


# ── Deterministic test embedding provider (no network / ollama required) ────
class HashEmbeddingProvider(BaseEmbeddingProvider):
    """Tiny deterministic hash-based embedder. Pure-Python, offline, fast.

    Produces 64-dim vectors seeded by a word-level rolling hash — stable
    across runs, no model download, and different-enough per text to let
    cosine similarity rank chunks roughly correctly for the tests.
    """

    DIM = 64

    def embed_texts(self, texts):
        return [self._embed(t) for t in texts]

    def embed_query(self, query: str):
        return self._embed(query)

    @property
    def dimension(self) -> int:
        return self.DIM

    @classmethod
    def _embed(cls, text: str):
        vec = [0.0] * cls.DIM
        if not text:
            return vec
        for word in text.lower().split():
            h = int(hashlib.md5(word.encode()).hexdigest(), 16)
            idx = h % cls.DIM
            vec[idx] += 1.0
        # L2 normalize so cosine distance is meaningful
        norm = sum(x * x for x in vec) ** 0.5 or 1.0
        return [x / norm for x in vec]


# ── Test harness ──────────────────────────────────────────────────────────
class TestRunner:
    def __init__(self):
        self.results: list[tuple[str, str, str]] = []  # (name, status, info)
        self.tmp: Path | None = None
        self.store: VectorKnowledgeStore | None = None
        self.pipeline: DocumentIngestionPipeline | None = None

    def setup(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="lumen_kb_test_"))
        self.store = VectorKnowledgeStore(
            persist_dir=str(self.tmp),
            embedding_provider=HashEmbeddingProvider(),
            collection_name="itest_collection",
        )
        self.pipeline = DocumentIngestionPipeline(self.store)

    def teardown(self):
        if self.tmp and self.tmp.exists():
            shutil.rmtree(self.tmp, ignore_errors=True)

    def _record(self, name, ok, info=""):
        status = "PASS" if ok else "FAIL"
        self.results.append((name, status, info))
        print(f"  [{status}] {name} {('— ' + info) if info else ''}")

    def check(self, name, cond, info=""):
        self._record(name, bool(cond), info)
        return bool(cond)

    # ── individual tests ────────────────────────────────────────────────
    def test_empty_state(self):
        s = self.store.get_stats()
        self.check("empty store: total_chunks==0", s["total_chunks"] == 0, str(s))
        self.check("empty store: total_documents==0", s["total_documents"] == 0)
        self.check("empty store: services==[]", s["services"] == [])
        self.check("empty store: get_all_doc_ids==[]", self.store.get_all_doc_ids() == [])

    def test_single_ingest(self):
        content = (
            "# Tax Invoice Service\n\n"
            "Handles electronic tax invoices for CoreTax.\n\n"
            "## Endpoints\n\n"
            "- POST /api/invoices — submit\n"
            "- GET /api/invoices/{id} — fetch\n"
        )
        n = self.store.ingest_document(
            content,
            {"service_name": "InvoiceSvc", "chunk_type": "general"},
            doc_id="doc_invoice",
        )
        self.check("single ingest returns positive chunk count", n > 0, f"{n} chunks")
        s = self.store.get_stats()
        self.check("single ingest: total_chunks matches", s["total_chunks"] == n)
        self.check("single ingest: total_documents==1", s["total_documents"] == 1)
        self.check("single ingest: service recorded", "InvoiceSvc" in s["services"])
        self.check(
            "single ingest: get_all_doc_ids has doc_invoice",
            "doc_invoice" in self.store.get_all_doc_ids(),
        )
        return n

    def test_same_doc_id_replace(self, original_count: int):
        """Critical: re-ingesting SAME doc_id must REPLACE, not duplicate."""
        new_content = (
            "# Tax Invoice Service (v2)\n\n"
            "Updated description with more content.\n\n"
            "## Endpoints\n\n"
            "- POST /api/invoices\n- GET /api/invoices/{id}\n- DELETE /api/invoices/{id}\n"
        )
        before = self.store.get_stats()["total_chunks"]
        n = self.store.ingest_document(
            new_content,
            {"service_name": "InvoiceSvc", "chunk_type": "general"},
            doc_id="doc_invoice",
        )
        after = self.store.get_stats()["total_chunks"]
        # New total must equal new chunks (old chunks gone), NOT old+new.
        self.check(
            "re-ingest same doc_id: replaces (not adds)",
            after == n,
            f"before={before} after={after} new_chunks={n}",
        )
        self.check(
            "re-ingest same doc_id: still exactly 1 document",
            self.store.get_stats()["total_documents"] == 1,
        )

    def test_different_doc_ids_accumulate(self):
        """Different doc_ids must ADD, not replace."""
        before = self.store.get_stats()["total_chunks"]
        n1 = self.store.ingest_document(
            "# Payment Service\n\nHandles payment processing for tax filings.",
            {"service_name": "PaymentSvc"},
            doc_id="doc_payment",
        )
        n2 = self.store.ingest_document(
            "# Notification Service\n\nSends SMS and email notifications.",
            {"service_name": "NotificationSvc"},
            doc_id="doc_notification",
        )
        after = self.store.get_stats()["total_chunks"]
        self.check(
            "different doc_ids accumulate",
            after == before + n1 + n2,
            f"before={before} after={after} added={n1 + n2}",
        )
        self.check(
            "total_documents==3 after two new ingests",
            self.store.get_stats()["total_documents"] == 3,
        )
        services = set(self.store.get_stats()["services"])
        self.check(
            "all three services recorded",
            {"InvoiceSvc", "PaymentSvc", "NotificationSvc"} <= services,
            str(sorted(services)),
        )

    def test_query(self):
        results = self.store.query("payment processing flow", top_k=5)
        self.check("query returns results", len(results) > 0, f"{len(results)} chunks")
        if results:
            top = results[0]
            self.check(
                "query results have content",
                bool(top.content),
                f"top score={top.score:.3f}",
            )

    def test_query_with_filter(self):
        results = self.store.query(
            "service",
            top_k=10,
            filters={"service_name": "PaymentSvc"},
        )
        self.check(
            "filtered query returns only PaymentSvc",
            all(r.metadata.service_name == "PaymentSvc" for r in results),
            f"{len(results)} chunks, services={set(r.metadata.service_name for r in results)}",
        )

    def test_delete(self):
        before = self.store.get_stats()["total_chunks"]
        before_docs = self.store.get_stats()["total_documents"]
        ok = self.store.delete_document("doc_notification")
        after = self.store.get_stats()["total_chunks"]
        after_docs = self.store.get_stats()["total_documents"]
        self.check("delete returns True", ok)
        self.check(
            "delete reduces chunk count",
            after < before,
            f"before={before} after={after}",
        )
        self.check(
            "delete reduces document count",
            after_docs == before_docs - 1,
            f"before={before_docs} after={after_docs}",
        )
        self.check(
            "deleted doc_id gone from get_all_doc_ids",
            "doc_notification" not in self.store.get_all_doc_ids(),
        )

    def test_pipeline_markdown_file(self):
        md_path = self.tmp / "sample.md"
        md_path.write_text(
            "# Sample Doc\n\nPipeline ingest test for markdown files.\n",
            encoding="utf-8",
        )
        before = self.store.get_stats()["total_chunks"]
        chunks = self.pipeline.ingest_markdown_file(
            str(md_path), metadata={"service_name": "SampleSvc"}
        )
        after = self.store.get_stats()["total_chunks"]
        self.check(
            "pipeline.ingest_markdown_file grows store",
            after > before and chunks > 0,
            f"before={before} after={after} chunks={chunks}",
        )

        # Re-ingesting same file should REPLACE (deterministic path-hash doc_id)
        re_chunks = self.pipeline.ingest_markdown_file(
            str(md_path), metadata={"service_name": "SampleSvc"}
        )
        after2 = self.store.get_stats()["total_chunks"]
        self.check(
            "pipeline.ingest_markdown_file re-ingest REPLACES (idempotent by path)",
            after2 == after,
            f"first={after} second={after2} re_chunks={re_chunks}",
        )

    def test_pipeline_markdown_directory(self):
        dir_path = self.tmp / "md_dir"
        dir_path.mkdir(exist_ok=True)
        for i in range(3):
            (dir_path / f"file_{i}.md").write_text(
                f"# Doc {i}\n\nContent of document number {i}.\n",
                encoding="utf-8",
            )
        before = self.store.get_stats()["total_chunks"]
        result = self.pipeline.ingest_markdown_directory(
            str(dir_path), metadata={"batch": "test"}
        )
        after = self.store.get_stats()["total_chunks"]
        self.check(
            "directory ingest processes all files",
            result["files_processed"] == 3,
            str(result),
        )
        self.check(
            "directory ingest grows store",
            after > before,
            f"before={before} after={after}",
        )

    def test_upload_tab_md5_pattern(self):
        """Simulate the Knowledge Store Upload tab doc_id scheme:
        md5(f"{filename}:{len(raw_bytes)}")."""
        raw = b"# Uploaded PDF\n\nSome extracted text from a PDF upload."
        name = "CoreTax_FSD.pdf"
        doc_id = hashlib.md5(f"{name}:{len(raw)}".encode()).hexdigest()

        before = self.store.get_stats()["total_chunks"]
        n1 = self.store.ingest_document(
            raw.decode("utf-8"),
            {"source_file": name, "doc_kind": "uploaded_pdf"},
            doc_id,
        )
        after1 = self.store.get_stats()["total_chunks"]

        # Same upload again → must replace
        n2 = self.store.ingest_document(
            raw.decode("utf-8"),
            {"source_file": name, "doc_kind": "uploaded_pdf"},
            doc_id,
        )
        after2 = self.store.get_stats()["total_chunks"]

        self.check(
            "upload: first ingest grows store",
            after1 == before + n1,
            f"before={before} after={after1} n1={n1}",
        )
        self.check(
            "upload: same file re-ingest replaces (idempotent)",
            after2 == after1 and n1 == n2,
            f"first={after1} second={after2} n2={n2}",
        )

        # Different content, same name → different size → different doc_id
        raw2 = raw + b"\n\nAdditional paragraph."
        doc_id2 = hashlib.md5(f"{name}:{len(raw2)}".encode()).hexdigest()
        n3 = self.store.ingest_document(
            raw2.decode("utf-8"),
            {"source_file": name, "doc_kind": "uploaded_pdf"},
            doc_id2,
        )
        after3 = self.store.get_stats()["total_chunks"]
        self.check(
            "upload: different size → different doc_id → accumulates",
            after3 == after2 + n3 and doc_id != doc_id2,
            f"after={after3}",
        )

    def test_crawl_report_deterministic_ids(self):
        """Simulate ingest_crawl_report with a minimal fake report object."""
        from src.models.crawler import CrawlReport, ProjectInfo, EndpointInfo

        report = CrawlReport(
            solution="CoreTaxSample.sln",
            projects=[
                ProjectInfo(
                    name="CoreTax.Api",
                    path="/fake/CoreTax.Api.csproj",
                    layer="api",
                    framework="net8.0",
                    references=["CoreTax.Core"],
                    nuget_packages=[],
                ),
            ],
            endpoints=[
                EndpointInfo(
                    route="/api/invoices",
                    method="POST",
                    controller="InvoiceController",
                    handler="Submit",
                    file="InvoiceController.cs",
                    line=42,
                    auth_required=True,
                ),
            ],
            consumers=[],
            schedulers=[],
            integrations=[],
            data_models=[],
            ui_components=[],
        )

        before = self.store.get_stats()["total_chunks"]
        n1 = self.pipeline.ingest_crawl_report(report)
        after1 = self.store.get_stats()["total_chunks"]
        self.check(
            "crawl report: first ingest adds chunks",
            n1 > 0 and after1 > before,
            f"before={before} after={after1} n1={n1}",
        )

        # Re-ingest same report → deterministic doc_ids replace everything
        n2 = self.pipeline.ingest_crawl_report(report)
        after2 = self.store.get_stats()["total_chunks"]
        self.check(
            "crawl report: re-ingest REPLACES (no growth)",
            after2 == after1 and n1 == n2,
            f"first={after1} second={after2} n2={n2}",
        )

        # Modify report (new solution name) → different doc_ids → growth
        report2 = report.model_copy(update={"solution": "OtherSolution.sln"})
        n3 = self.pipeline.ingest_crawl_report(report2)
        after3 = self.store.get_stats()["total_chunks"]
        self.check(
            "crawl report: new solution name → new doc_ids → grows",
            after3 == after2 + n3,
            f"after={after3} n3={n3}",
        )

    def test_unicode_and_edge_cases(self):
        # Unicode
        before = self.store.get_stats()["total_chunks"]
        n = self.store.ingest_document(
            "# 税务发票服务\n\nПроцессинг платежей. 🇮🇩 Indonesian tax context.",
            {"service_name": "UnicodeSvc"},
            "doc_unicode",
        )
        after = self.store.get_stats()["total_chunks"]
        self.check("unicode content ingests", n > 0 and after > before)

        # Empty string → 0 chunks
        n_empty = self.store.ingest_document("", {"service_name": "Empty"}, "doc_empty")
        self.check("empty content → 0 chunks", n_empty == 0)

        # Whitespace-only
        n_ws = self.store.ingest_document("   \n\n   ", {}, "doc_ws")
        self.check("whitespace-only content → 0 chunks", n_ws == 0)

        # Metadata with None value (should be coerced to "")
        n_meta = self.store.ingest_document(
            "# None meta\n\nContent.",
            {"service_name": None, "probis_domain": None},
            "doc_none_meta",
        )
        self.check("None metadata values handled", n_meta > 0)

    def test_rebuild_index(self):
        before = self.store.get_stats()["total_chunks"]
        self.check("pre-rebuild: store not empty", before > 0, f"{before} chunks")
        self.store.rebuild_index()
        after = self.store.get_stats()["total_chunks"]
        self.check("rebuild_index: store empty afterward", after == 0, f"{after} chunks")
        self.check(
            "rebuild_index: get_all_doc_ids empty",
            self.store.get_all_doc_ids() == [],
        )

    def test_stats_consistency(self):
        """get_stats() and get_all_doc_ids() must agree after every mutation."""
        # Starting from empty (post-rebuild)
        for i in range(5):
            self.store.ingest_document(
                f"# Doc {i}\n\nContent body {i}.",
                {"service_name": f"Svc{i}"},
                f"doc_stat_{i}",
            )
        stats = self.store.get_stats()
        ids = self.store.get_all_doc_ids()
        self.check(
            "stats.total_documents == len(get_all_doc_ids)",
            stats["total_documents"] == len(ids),
            f"stats={stats['total_documents']} ids={len(ids)}",
        )
        self.check(
            "services include Svc0..Svc4 from this test",
            all(f"Svc{i}" in stats["services"] for i in range(5)),
            f"services={stats['services']}",
        )

    # ── main ────────────────────────────────────────────────────────────
    def run(self):
        print("\n=== KNOWLEDGE STORE INTEGRATION TEST ===\n")
        self.setup()
        try:
            print("[1] Empty state")
            self.test_empty_state()

            print("\n[2] Single ingest")
            n = self.test_single_ingest()

            print("\n[3] Same doc_id re-ingest (replace)")
            self.test_same_doc_id_replace(n)

            print("\n[4] Different doc_ids accumulate")
            self.test_different_doc_ids_accumulate()

            print("\n[5] Query retrieval")
            self.test_query()

            print("\n[6] Query with metadata filter")
            self.test_query_with_filter()

            print("\n[7] Delete document")
            self.test_delete()

            print("\n[8] Pipeline.ingest_markdown_file")
            self.test_pipeline_markdown_file()

            print("\n[9] Pipeline.ingest_markdown_directory")
            self.test_pipeline_markdown_directory()

            print("\n[10] Upload-tab md5 doc_id pattern")
            self.test_upload_tab_md5_pattern()

            print("\n[11] Pipeline.ingest_crawl_report")
            self.test_crawl_report_deterministic_ids()

            print("\n[12] Unicode and edge cases")
            self.test_unicode_and_edge_cases()

            print("\n[13] Stats consistency")
            self.test_stats_consistency()

            print("\n[14] Rebuild index")
            self.test_rebuild_index()
        except Exception as e:
            print(f"\n!!! Uncaught exception during test: {e}")
            traceback.print_exc()
            self._record("uncaught_exception", False, str(e))
        finally:
            self.teardown()

        # Summary
        total = len(self.results)
        passed = sum(1 for _, s, _ in self.results if s == "PASS")
        failed = total - passed
        print(f"\n=== SUMMARY: {passed}/{total} passed, {failed} failed ===")
        if failed:
            print("\nFAILURES:")
            for name, status, info in self.results:
                if status == "FAIL":
                    print(f"  - {name}: {info}")
        return failed == 0


if __name__ == "__main__":
    ok = TestRunner().run()
    sys.exit(0 if ok else 1)
