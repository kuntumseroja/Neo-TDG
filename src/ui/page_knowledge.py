"""Knowledge Store management page."""

import hashlib
import logging

import streamlit as st
from pathlib import Path

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

    tab1, tab_upload, tab2, tab3 = st.tabs(
        ["Markdown Files", "Upload File (PDF/MD)", "TechDocGen Output", "Rebuild"]
    )

    with tab_upload:
        st.caption(
            "Upload a Markdown or PDF file directly from your machine — "
            "no path required. PDFs are text-extracted page-by-page via "
            "`pypdf` and ingested as a single document. Re-uploading the "
            "same file **replaces** its existing chunks (idempotent by "
            "name+size hash) — the total count only grows when you "
            "ingest a **different** document."
        )
        uploaded = st.file_uploader(
            "Choose a .md or .pdf file",
            type=["md", "markdown", "txt", "pdf"],
            key="kb_upload_file",
            accept_multiple_files=False,
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
            if not uploaded:
                st.error("Please choose a file to upload first.")
            else:
                try:
                    raw = uploaded.getvalue()
                    name = uploaded.name
                    suffix = Path(name).suffix.lower()
                    # Snapshot the total chunk count BEFORE ingest so we
                    # can report an accurate delta even when the store
                    # replaces existing chunks (idempotent by doc_id).
                    before_total = store.get_stats().get("total_chunks", 0)
                    with st.spinner(f"Extracting and ingesting {name}..."):
                        if suffix == ".pdf":
                            content = _extract_pdf_text(raw)
                            doc_kind = "uploaded_pdf"
                        else:
                            content = raw.decode("utf-8", errors="ignore")
                            doc_kind = "uploaded_markdown"

                        if not content.strip():
                            st.error(
                                "No extractable text in the file. "
                                "Scanned PDFs (image-only) need OCR first."
                            )
                        else:
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
                            after_total = store.get_stats().get("total_chunks", 0)
                            delta = after_total - before_total
                            delta_str = (
                                f"+{delta}" if delta > 0
                                else f"{delta}" if delta < 0
                                else "±0 (replaced existing)"
                            )
                            st.success(
                                f"Ingested **{name}** "
                                f"({len(content):,} chars) → "
                                f"**{chunks}** chunks for this document. "
                                f"Store total: **{before_total} → {after_total}** "
                                f"({delta_str})"
                            )
                            with st.expander("Preview extracted text", expanded=False):
                                st.text(
                                    content[:4000]
                                    + ("\n\n... (truncated)" if len(content) > 4000 else "")
                                )
                            # Force a rerun so the Total Chunks / Documents
                            # metrics at the top of the page pick up the
                            # fresh count instead of showing the pre-ingest
                            # snapshot from the start of this render pass.
                            st.rerun()
                except Exception as e:
                    logger.exception("Upload ingest failed")
                    st.error(f"Ingest failed: {e}")

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

            before_total = store.get_stats().get("total_chunks", 0)
            with st.spinner("Ingesting documents..."):
                if path.is_file():
                    chunks = pipeline.ingest_markdown_file(str(path), metadata)
                    after_total = store.get_stats().get("total_chunks", 0)
                    delta = after_total - before_total
                    delta_str = f"+{delta}" if delta >= 0 else str(delta)
                    st.success(
                        f"Ingested 1 file: {chunks} chunks for this document. "
                        f"Store total: **{before_total} → {after_total}** ({delta_str})"
                    )
                    st.rerun()
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
                    after_total = store.get_stats().get("total_chunks", 0)
                    delta = after_total - before_total
                    delta_str = f"+{delta}" if delta >= 0 else str(delta)
                    st.success(
                        f"Ingested {result['files_processed']}/{result['total_files']} files: "
                        f"{result['total_chunks']} chunks for these documents. "
                        f"Store total: **{before_total} → {after_total}** ({delta_str})"
                    )
                    st.rerun()
                else:
                    st.error(f"Path not found: {ingest_path}")

    with tab2:
        tdg_docs_dir = st.text_input(
            "TechDocGen docs directory",
            value=str(Path(__file__).resolve().parent.parent.parent.parent / "TechDocGen" / "docs"),
            key="tdg_docs_dir",
        )
        if st.button("Ingest TechDocGen Output", type="primary", key="btn_ingest_tdg"):
            if not Path(tdg_docs_dir).exists():
                st.error(f"Directory not found: {tdg_docs_dir}")
            else:
                before_total = store.get_stats().get("total_chunks", 0)
                with st.spinner("Ingesting TechDocGen output..."):
                    result = pipeline.ingest_markdown_directory(
                        tdg_docs_dir,
                        metadata={"source": "techdocgen"},
                    )
                    after_total = store.get_stats().get("total_chunks", 0)
                    delta = after_total - before_total
                    delta_str = (
                        f"+{delta}" if delta > 0
                        else f"{delta}" if delta < 0
                        else "±0 (replaced existing)"
                    )
                    st.success(
                        f"Ingested {result['files_processed']} files: "
                        f"{result['total_chunks']} chunks for these documents. "
                        f"Store total: **{before_total} → {after_total}** ({delta_str})"
                    )
                    st.rerun()

    with tab3:
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
                    after_total = store.get_stats().get("total_chunks", 0)
                    st.success(
                        f"Rebuilt index: {result['files_processed']} files, "
                        f"{result['total_chunks']} chunks. "
                        f"Store total now: **{after_total}**"
                    )
                    st.rerun()

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
