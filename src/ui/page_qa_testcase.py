"""QA Test Case Generator page — BRD (PDF/DOCX) to Test Cases.

Upload a Business Requirements Document, extract requirements via LLM,
generate traceable test cases, preview/download, and optionally ingest
the result into the knowledge store for RAG retrieval.
"""

import hashlib
import logging
from datetime import datetime

import streamlit as st

from src.ui.components import (
    render_carbon_tag,
    render_markdown_with_mermaid,
)

try:
    from src.ui.theme import (
        BLUE as CARBON_BLUE_60,
        GREEN as CARBON_GREEN_60,
        RED as CARBON_RED_60,
        GRAY_70 as CARBON_GRAY_70,
        GRAY_100 as CARBON_GRAY_100,
        YELLOW_30 as CARBON_YELLOW_30,
        FONT_FAMILY as CARBON_FONT,
        BG_SOFT,
        SOFT_BLUE,
        RADIUS_MD,
        SHADOW_SOFT,
    )
except ImportError:
    CARBON_BLUE_60 = "#0f62fe"
    CARBON_GREEN_60 = "#198038"
    CARBON_RED_60 = "#da1e28"
    CARBON_GRAY_70 = "#525252"
    CARBON_GRAY_100 = "#161616"
    CARBON_YELLOW_30 = "#f1c21b"
    CARBON_FONT = "'IBM Plex Sans', system-ui, sans-serif"
    BG_SOFT = "#f8faff"
    SOFT_BLUE = "#d0e2ff"
    RADIUS_MD = "6px"
    SHADOW_SOFT = "0 1px 3px rgba(0,0,0,0.08)"

logger = logging.getLogger(__name__)


def render_qa_testcase():
    """Render the QA BRD-to-TestCase page."""
    st.header("QA Test Case Generator")
    st.caption(
        "Upload a BRD (PDF or Word) to extract requirements and "
        "generate traceable test cases. Results can be downloaded or "
        "ingested into the knowledge store for RAG retrieval."
    )

    llm = st.session_state.get("llm")
    pipeline = st.session_state.get("pipeline")
    store = st.session_state.get("store")

    if not llm:
        st.warning(
            "LLM not initialized. Please configure and connect to Ollama "
            "in the sidebar first."
        )
        return

    # ── File upload ──────────────────────────────────────────────────
    uploaded = st.file_uploader(
        "Upload BRD document",
        type=["pdf", "docx", "doc", "md", "txt"],
        key="qa_brd_upload",
        help="Supports PDF, Word (.docx), Markdown, and plain text.",
    )

    # ── Optional metadata ────────────────────────────────────────────
    meta_col1, meta_col2 = st.columns(2)
    with meta_col1:
        project_name = st.text_input(
            "Project / Service Name (optional)",
            key="qa_project_name",
            placeholder="e.g. CoreTax Invoice Module",
        )
    with meta_col2:
        brd_version = st.text_input(
            "BRD Version (optional)",
            key="qa_brd_version",
            placeholder="e.g. v1.2",
        )

    # ── Generate button ──────────────────────────────────────────────
    gen_col, ingest_col = st.columns(2)
    with gen_col:
        btn_generate = st.button(
            "Generate Test Cases",
            type="primary",
            disabled=not uploaded,
            key="btn_qa_generate",
        )
    with ingest_col:
        btn_ingest = st.button(
            "Ingest to Knowledge Store",
            disabled=not st.session_state.get("qa_report_md"),
            key="btn_qa_ingest",
        )

    # ── Generation flow ──────────────────────────────────────────────
    if btn_generate and uploaded:
        from src.sdlc.brd_test_generator import BRDTestCaseGenerator

        raw = uploaded.getvalue()
        if not raw:
            st.error("Uploaded file is empty.")
            return

        generator = BRDTestCaseGenerator(llm=llm)

        try:
            # Step 1: Extract requirements
            with st.spinner("Extracting requirements from BRD..."):
                from src.sdlc.brd_test_generator import extract_text
                brd_text = extract_text(uploaded.name, raw)
                if not brd_text.strip():
                    st.error(
                        "No extractable text found. Scanned PDFs "
                        "(image-only) require OCR first."
                    )
                    return
                st.info(
                    f"Extracted **{len(brd_text):,}** characters from "
                    f"`{uploaded.name}`."
                )
                reqs = generator.extract_requirements(brd_text)

            if not reqs:
                st.error(
                    "Could not extract any requirements. The document "
                    "may not contain structured business requirements."
                )
                return

            st.success(
                f"Extracted **{len(reqs)}** requirements "
                f"({sum(1 for r in reqs if r.priority in ('high','critical'))}"
                f" high/critical)."
            )

            # Step 2: Generate test cases
            with st.spinner(
                f"Generating test cases for {len(reqs)} requirements..."
            ):
                cases = generator.generate_test_cases(reqs)

            if not cases:
                st.warning(
                    "LLM returned no test cases. Try a different model "
                    "or re-upload the document."
                )
                return

            # Step 3: Build report
            report = generator.build_report(uploaded.name, reqs, cases)
            md = generator.to_markdown(report)

            # Persist in session state
            st.session_state.qa_report = report
            st.session_state.qa_report_md = md
            st.session_state.qa_brd_filename = uploaded.name

            st.success(
                f"Generated **{len(cases)}** test cases across "
                f"**{len(reqs)}** requirements. "
                f"Coverage: **{report.coverage_pct}%**"
            )
            st.rerun()

        except Exception as e:
            logger.exception("BRD-to-TestCase failed")
            st.error(f"Generation failed: {e}")
            return

    # ── Ingest to knowledge store ────────────────────────────────────
    if btn_ingest:
        md = st.session_state.get("qa_report_md")
        filename = st.session_state.get("qa_brd_filename", "brd_testcases")
        if not md:
            st.error("No report to ingest. Generate test cases first.")
        elif not pipeline:
            st.error("Knowledge store pipeline not initialized.")
        else:
            before_total = store.get_stats().get("total_chunks", 0) if store else 0
            with st.spinner("Ingesting test cases into knowledge store..."):
                doc_id = "qa_testcases_" + hashlib.md5(
                    f"{filename}:{len(md)}".encode()
                ).hexdigest()
                metadata = {
                    "source_file": filename,
                    "doc_kind": "qa_test_cases",
                    "chunk_type": "test_case",
                }
                if project_name:
                    metadata["service_name"] = project_name
                chunks = pipeline.store.ingest_document(md, metadata, doc_id)
                after_total = store.get_stats().get("total_chunks", 0) if store else 0
                delta = after_total - before_total
                delta_str = (
                    f"+{delta}" if delta > 0
                    else f"{delta}" if delta < 0
                    else "±0 (replaced existing)"
                )
                st.success(
                    f"Ingested **{chunks}** chunks. "
                    f"Store total: **{before_total} → {after_total}** "
                    f"({delta_str})"
                )
                st.rerun()

    # ── Display results ──────────────────────────────────────────────
    report = st.session_state.get("qa_report")
    md = st.session_state.get("qa_report_md")
    if not report or not md:
        st.info(
            "Upload a BRD document and click **Generate Test Cases** "
            "to get started."
        )
        return

    # Metrics row
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Requirements", len(report.requirements))
    m2.metric("Test Cases", len(report.test_cases))
    m3.metric("Coverage", f"{report.coverage_pct}%")
    uncovered = sum(
        1 for r in report.requirements
        if r.req_id not in report.traceability
    )
    m4.metric("Uncovered Reqs", uncovered)

    # Download buttons
    st.divider()
    dl1, dl2, _sp = st.columns([1, 1, 2])
    timestamp = datetime.now().strftime("%m-%d-%Y")
    base_name = st.session_state.get("qa_brd_filename", "brd").rsplit(".", 1)[0]
    with dl1:
        st.download_button(
            "Download Test Cases (MD)",
            data=md,
            file_name=f"{base_name}_testcases_{timestamp}.md",
            mime="text/markdown",
            key="dl_qa_md",
        )
    with dl2:
        # CSV export of test cases
        csv_lines = [
            "TC_ID,Requirement,Title,Type,Priority,Preconditions,Steps,Expected Result"
        ]
        for tc in report.test_cases:
            steps_flat = " → ".join(tc.steps)
            csv_lines.append(
                f'"{tc.tc_id}","{tc.requirement_id}","{tc.title}",'
                f'"{tc.type}","{tc.priority}","{tc.preconditions}",'
                f'"{steps_flat}","{tc.expected_result}"'
            )
        csv_data = "\n".join(csv_lines)
        st.download_button(
            "Download Test Cases (CSV)",
            data=csv_data,
            file_name=f"{base_name}_testcases_{timestamp}.csv",
            mime="text/csv",
            key="dl_qa_csv",
        )

    # Tabs: Requirements | Test Cases | Traceability | Full Report
    tab_reqs, tab_cases, tab_trace, tab_full = st.tabs([
        "Requirements", "Test Cases", "Traceability Matrix", "Full Report"
    ])

    with tab_reqs:
        st.subheader(f"Requirements ({len(report.requirements)})")
        for r in report.requirements:
            pri_colors = {
                "critical": CARBON_RED_60,
                "high": "#ff832b",
                "medium": CARBON_YELLOW_30,
                "low": CARBON_GREEN_60,
            }
            pri_color = pri_colors.get(r.priority, CARBON_GRAY_70)
            pri_text = "#fff" if r.priority in ("critical", "high") else CARBON_GRAY_100

            with st.expander(f"{r.req_id}: {r.title}"):
                st.markdown(
                    f"{render_carbon_tag(r.priority.upper(), pri_color, pri_text)} "
                    f"{render_carbon_tag(r.category, CARBON_BLUE_60, '#fff')}",
                    unsafe_allow_html=True,
                )
                st.write(r.description)
                linked_tcs = report.traceability.get(r.req_id, [])
                if linked_tcs:
                    st.caption(f"Linked test cases: {', '.join(linked_tcs)}")
                else:
                    st.warning("No test cases linked to this requirement.")

    with tab_cases:
        st.subheader(f"Test Cases ({len(report.test_cases)})")

        # Filter by type
        types = sorted(set(tc.type for tc in report.test_cases))
        sel_type = st.selectbox(
            "Filter by type", ["all"] + types, key="qa_tc_type_filter"
        )
        filtered = (
            report.test_cases
            if sel_type == "all"
            else [tc for tc in report.test_cases if tc.type == sel_type]
        )

        for tc in filtered:
            type_colors = {
                "functional": CARBON_BLUE_60,
                "negative": CARBON_RED_60,
                "boundary": "#ff832b",
                "security": "#a2191f",
                "performance": CARBON_GREEN_60,
            }
            tc_color = type_colors.get(tc.type, CARBON_GRAY_70)
            with st.expander(f"{tc.tc_id}: {tc.title}"):
                st.markdown(
                    f"{render_carbon_tag(tc.type.upper(), tc_color, '#fff')} "
                    f"{render_carbon_tag(tc.priority, CARBON_GRAY_70, '#fff')} "
                    f"→ {tc.requirement_id}",
                    unsafe_allow_html=True,
                )
                if tc.preconditions:
                    st.markdown(f"**Preconditions:** {tc.preconditions}")
                st.markdown("**Steps:**")
                for i, step in enumerate(tc.steps, 1):
                    st.markdown(f"{i}. {step}")
                st.markdown(f"**Expected Result:** {tc.expected_result}")

    with tab_trace:
        st.subheader("Traceability Matrix")
        st.caption(
            "Maps each requirement to its test cases. "
            "Requirements without test cases are flagged."
        )
        for r in report.requirements:
            tcs = report.traceability.get(r.req_id, [])
            if tcs:
                icon = "✅"
                detail = ", ".join(tcs)
            else:
                icon = "❌"
                detail = "**NO COVERAGE**"
            st.markdown(
                f"{icon} **{r.req_id}** — {r.title} → {detail}"
            )

    with tab_full:
        st.subheader("Full Report")
        render_markdown_with_mermaid(md)
