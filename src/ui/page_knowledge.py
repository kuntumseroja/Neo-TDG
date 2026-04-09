"""Knowledge Store management page — supports local paths and GitHub URLs."""

import hashlib
import logging

import streamlit as st
from pathlib import Path
from src.readers.github_reader import GitHubReader

# Shared GitHub reader instance
_github_reader = GitHubReader()

logger = logging.getLogger(__name__)


def _extract_pdf_text(file_bytes: bytes) -> str:
    """Extract plain text from a PDF byte buffer using pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise RuntimeError(
            "pypdf is required to ingest PDFs. Install it with `pip install pypdf`."
        ) from e
    import io
    reader = PdfReader(io.BytesIO(file_bytes))
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception as e:
            logger.warning(f"PDF page {i} extraction failed: {e}")
            text = ""
        if text.strip():
            pages.append(f"## Page {i}\n\n{text.strip()}")
    return "\n\n".join(pages)


def render_knowledge_management():
    """Render the knowledge store management page."""
    st.header("Knowledge Store")

    store = st.session_state.get("store")
    pipeline = st.session_state.get("pipeline")

    if not store:
        st.warning("Knowledge store not initialized.")
        return

    # Stats dashboard
    stats = store.get_stats()
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Chunks", stats.get("total_chunks", 0))
    with col2:
        st.metric("Documents", stats.get("total_documents", 0))
    with col3:
        st.metric("Services", len(stats.get("services", [])))
    with col4:
        st.metric("Collection", stats.get("collection_name", ""))

    # Chunk type distribution
    chunk_types = stats.get("chunk_types", {})
    if chunk_types:
        st.subheader("Chunk Types")
        cols = st.columns(len(chunk_types))
        for i, (ct, count) in enumerate(sorted(chunk_types.items())):
            with cols[i % len(cols)]:
                st.metric(ct, count)

    # Services
    services = stats.get("services", [])
    if services:
        st.subheader("Indexed Services")
        st.write(", ".join(services))

    st.divider()

    # Ingest section
    st.subheader("Ingest Documents")

    # Five tabs: local markdown ingest, direct file upload (PDF/MD),
    # GitHub repo clone-and-ingest, TechDocGen output, and index rebuild.
    tab1, tab_upload, tab2, tab3, tab4 = st.tabs(
        [
            "📁 Markdown Files",
            "⬆️ Upload File (PDF/MD)",
            "🔗 GitHub Repository",
            "📦 TechDocGen Output",
            "🔄 Rebuild",
        ]
    )

    with tab_upload:
        st.caption(
            "Upload a Markdown or PDF file directly from your machine — "
            "no path required. PDFs are text-extracted page-by-page via "
            "`pypdf` and ingested as a single document."
        )
        uploaded = st.file_uploader(
            "Choose one or more .md / .pdf files",
            type=["md", "markdown", "txt", "pdf"],
            key="kb_upload_file",
            accept_multiple_files=True,
            help=(
                "If files appear with a red ⚠ icon on HF Spaces, the "
                "iframe's XSRF cookie was blocked. The Space config sets "
                "enableXsrfProtection=false to work around this — redeploy "
                "if you still see rejections."
            ),
        )
        u_col1, u_col2 = st.columns(2)
        with u_col1:
            up_service = st.text_input(
                "Service Name (optional)", key="kb_upload_service"
            )
        with u_col2:
            up_probis = st.text_input(
                "Probis Domain (optional)", key="kb_upload_probis"
            )

        if st.button(
            "Ingest Uploaded File", type="primary", key="btn_kb_upload_ingest"
        ):
            # Normalize to a list — accept_multiple_files=True returns a
            # list, but older sessions / single-file selections may still
            # surface a single UploadedFile object.
            if not uploaded:
                files = []
            elif isinstance(uploaded, list):
                files = uploaded
            else:
                files = [uploaded]

            if not files:
                st.error(
                    "Please choose a file to upload first. If you see a "
                    "red ⚠ next to a file name, Streamlit's XSRF check "
                    "rejected it server-side — this is fixed in the "
                    "current .streamlit/config.toml; redeploy the Space "
                    "if it persists."
                )
            else:
                before_total = (
                    store.get_stats().get("total_chunks", 0) if store else 0
                )
                results = []
                for up in files:
                    name = getattr(up, "name", "<unknown>")
                    try:
                        raw = up.getvalue()
                    except Exception as e:
                        logger.exception("Upload read failed for %s", name)
                        results.append((name, "error", f"read failed: {e}"))
                        continue
                    if not raw:
                        results.append(
                            (name, "error", "empty file (rejected by Streamlit?)")
                        )
                        continue
                    suffix = Path(name).suffix.lower()
                    try:
                        with st.spinner(f"Extracting and ingesting {name}..."):
                            if suffix == ".pdf":
                                content = _extract_pdf_text(raw)
                                doc_kind = "uploaded_pdf"
                            else:
                                content = raw.decode("utf-8", errors="ignore")
                                doc_kind = "uploaded_markdown"

                            if not content.strip():
                                results.append(
                                    (
                                        name,
                                        "error",
                                        "no extractable text (scanned PDF?)",
                                    )
                                )
                                continue

                            metadata = {
                                "source_file": name,
                                "doc_kind": doc_kind,
                            }
                            if up_service:
                                metadata["service_name"] = up_service
                            if up_probis:
                                metadata["probis_domain"] = up_probis

                            doc_id = hashlib.md5(
                                f"{name}:{len(raw)}".encode()
                            ).hexdigest()
                            chunks = pipeline.store.ingest_document(
                                content, metadata, doc_id
                            )
                            results.append(
                                (name, "ok", f"{chunks} chunks ({len(content):,} chars)")
                            )
                    except Exception as e:
                        logger.exception("Upload ingest failed for %s", name)
                        results.append((name, "error", str(e)))

                after_total = (
                    store.get_stats().get("total_chunks", 0) if store else 0
                )
                delta = after_total - before_total
                delta_str = (
                    f"+{delta}" if delta > 0
                    else f"{delta}" if delta < 0
                    else "±0 (replaced existing)"
                )

                ok_count = sum(1 for _, s, _ in results if s == "ok")
                err_count = sum(1 for _, s, _ in results if s == "error")

                if ok_count:
                    st.success(
                        f"Ingested **{ok_count}/{len(results)}** file(s). "
                        f"Store total: **{before_total} → {after_total}** "
                        f"({delta_str})"
                    )
                if err_count:
                    st.error(f"{err_count} file(s) failed — see details below.")

                with st.expander("Per-file result", expanded=bool(err_count)):
                    for name, status, info in results:
                        icon = "✅" if status == "ok" else "❌"
                        st.write(f"{icon} **{name}** — {info}")

                if ok_count:
                    st.rerun()

    with tab1:
        ingest_path = st.text_input(
            "Path to file or directory",
            placeholder="/path/to/docs/ or /path/to/file.md",
            key="ingest_path",
        )
        col1, col2 = st.columns(2)
        with col1:
            service_name = st.text_input("Service Name (optional)", key="ingest_service")
        with col2:
            probis_domain = st.text_input("Probis Domain (optional)", key="ingest_probis")

        if st.button("Ingest", type="primary", key="btn_ingest"):
            if not ingest_path:
                st.error("Please enter a path.")
                return

            path = Path(ingest_path)
            metadata = {}
            if service_name:
                metadata["service_name"] = service_name
            if probis_domain:
                metadata["probis_domain"] = probis_domain

            with st.spinner("Ingesting documents..."):
                if path.is_file():
                    chunks = pipeline.ingest_markdown_file(str(path), metadata)
                    st.success(f"Ingested 1 file: {chunks} chunks created.")
                elif path.is_dir():
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    def progress_cb(current, total, filename):
                        progress_bar.progress(current / total if total else 0)
                        status_text.text(f"Processing: {filename}")

                    result = pipeline.ingest_markdown_directory(
                        str(path), metadata=metadata, progress_callback=progress_cb,
                    )
                    progress_bar.progress(1.0)
                    st.success(
                        f"Ingested {result['files_processed']}/{result['total_files']} files: "
                        f"{result['total_chunks']} chunks created."
                    )
                else:
                    st.error(f"Path not found: {ingest_path}")

    with tab2:
        _render_github_ingest_tab(pipeline)

    with tab3:
        tdg_docs_dir = st.text_input(
            "TechDocGen docs directory",
            value=str(Path(__file__).resolve().parent.parent.parent.parent / "TechDocGen" / "docs"),
            key="tdg_docs_dir",
        )
        if st.button("Ingest TechDocGen Output", type="primary", key="btn_ingest_tdg"):
            if not Path(tdg_docs_dir).exists():
                st.error(f"Directory not found: {tdg_docs_dir}")
            else:
                with st.spinner("Ingesting TechDocGen output..."):
                    result = pipeline.ingest_markdown_directory(
                        tdg_docs_dir,
                        metadata={"source": "techdocgen"},
                    )
                    st.success(
                        f"Ingested {result['files_processed']} files: "
                        f"{result['total_chunks']} chunks created."
                    )

    with tab4:
        st.warning("This will drop all existing data and rebuild from scratch.")
        rebuild_dir = st.text_input("Directory to rebuild from", key="rebuild_dir")
        if st.button("Rebuild Index", type="secondary", key="btn_rebuild"):
            if not rebuild_dir:
                st.error("Please enter a directory path.")
            elif not Path(rebuild_dir).exists():
                st.error(f"Directory not found: {rebuild_dir}")
            else:
                with st.spinner("Rebuilding index..."):
                    result = pipeline.full_rebuild(rebuild_dir)
                    st.success(
                        f"Rebuilt index: {result['files_processed']} files, "
                        f"{result['total_chunks']} chunks."
                    )

    st.divider()

    # Document browser
    st.subheader("Document Browser")
    doc_ids = store.get_all_doc_ids()

    if doc_ids:
        st.write(f"**{len(doc_ids)} documents** in the knowledge store:")
        for doc_id in doc_ids:
            col1, col2 = st.columns([4, 1])
            with col1:
                st.text(doc_id)
            with col2:
                if st.button("Delete", key=f"del_{doc_id}"):
                    store.delete_document(doc_id)
                    st.rerun()
    else:
        st.info("No documents in the knowledge store. Ingest some documents to get started.")


def _render_github_ingest_tab(pipeline):
    """Render the GitHub Repository ingest tab."""

    gh_url = st.text_input(
        "GitHub Repository URL",
        placeholder="https://github.com/owner/repo",
        key="gh_ingest_url",
    )
    gh_col1, gh_col2 = st.columns([3, 1])
    with gh_col1:
        gh_branch = st.text_input(
            "Branch (optional)",
            placeholder="main",
            key="gh_ingest_branch",
        )
    with gh_col2:
        gh_service = st.text_input(
            "Service Name (optional)",
            key="gh_ingest_service",
        )

    ingest_type = st.radio(
        "What to ingest",
        ["📄 Markdown files (.md)", "💻 All source code files", "📄 + 💻 Both"],
        key="gh_ingest_type",
        horizontal=True,
    )

    if not gh_url:
        st.info("Enter a GitHub repository URL to clone and ingest its contents.")
        return

    if not GitHubReader.is_github_url(gh_url):
        st.warning("Please enter a valid GitHub URL (https://github.com/owner/repo)")
        return

    if st.button("🔍 Clone & Ingest", type="primary", key="btn_gh_ingest"):
        clone_status = st.empty()
        try:
            # Step 1: Clone
            with st.spinner("Cloning repository..."):
                cloned_path = _github_reader.clone(
                    gh_url,
                    branch=gh_branch or None,
                    shallow=True,
                    progress_callback=lambda msg: clone_status.text(msg),
                )
                clone_status.empty()

            # Step 2: Discover files
            summary = GitHubReader.get_repo_summary(cloned_path)
            st.success(
                f"Cloned — {summary['total_files']} files, "
                f"{summary['md_count']} markdown, "
                f"{summary['sln_count']} solutions"
            )

            # Step 3: Ingest
            metadata = {"source": "github", "github_url": gh_url}
            if gh_service:
                metadata["service_name"] = gh_service

            total_chunks = 0

            # Ingest markdown files
            if ingest_type in ["📄 Markdown files (.md)", "📄 + 💻 Both"]:
                md_files = GitHubReader.find_markdown_files(cloned_path)
                if md_files:
                    with st.spinner(f"Ingesting {len(md_files)} markdown files..."):
                        progress_bar = st.progress(0)
                        for i, md_file in enumerate(md_files):
                            try:
                                chunks = pipeline.ingest_markdown_file(
                                    md_file, {**metadata, "source_file": md_file}
                                )
                                total_chunks += chunks
                            except Exception as e:
                                st.warning(f"Skipped {Path(md_file).name}: {e}")
                            progress_bar.progress((i + 1) / len(md_files))
                        progress_bar.progress(1.0)
                    st.info(f"Markdown: ingested {len(md_files)} files, {total_chunks} chunks")

            # Ingest source code files
            if ingest_type in ["💻 All source code files", "📄 + 💻 Both"]:
                source_files = GitHubReader.find_source_files(cloned_path)
                if source_files:
                    src_chunks = 0
                    with st.spinner(f"Ingesting {len(source_files)} source files..."):
                        progress_bar2 = st.progress(0)
                        for i, src_file in enumerate(source_files):
                            try:
                                chunks = pipeline.ingest_markdown_file(
                                    src_file,
                                    {**metadata, "source_file": src_file, "chunk_type": "source_code"},
                                )
                                src_chunks += chunks
                                total_chunks += chunks
                            except Exception:
                                pass  # Skip binary/unreadable files silently
                            progress_bar2.progress((i + 1) / len(source_files))
                        progress_bar2.progress(1.0)
                    st.info(f"Source code: ingested {len(source_files)} files, {src_chunks} chunks")

            st.success(f"✅ Total: {total_chunks} chunks ingested from {gh_url}")

        except Exception as e:
            clone_status.empty()
            st.error(f"Failed: {e}")
