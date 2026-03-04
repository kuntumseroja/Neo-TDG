"""Knowledge Store management page."""

import streamlit as st
from pathlib import Path


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

    tab1, tab2, tab3 = st.tabs(["Markdown Files", "TechDocGen Output", "Rebuild"])

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
