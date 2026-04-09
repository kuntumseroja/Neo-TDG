"""SDLC Tools page — Bug Assistant, Test Generator, Architecture Validator."""

import streamlit as st
from src.ui.components import (
    render_markdown_with_mermaid,
    render_carbon_tag,
    render_carbon_notification,
    stage_uploaded_file,
)


def render_sdlc_tools():
    """Render the SDLC tools page."""
    st.header("SDLC Tools")

    tab_bug, tab_test, tab_arch = st.tabs(
        ["Bug Resolution", "Test Generator", "Architecture Validator"]
    )

    with tab_bug:
        _render_bug_assistant()

    with tab_test:
        _render_test_generator()

    with tab_arch:
        _render_architecture_validator()


def _render_bug_assistant():
    """Bug resolution assistant."""
    st.subheader("Bug Resolution Assistant")

    description = st.text_area(
        "Bug Description",
        placeholder="Describe the bug or paste the error message...",
        height=100,
        key="bug_description",
    )
    stack_trace = st.text_area(
        "Stack Trace (optional)",
        placeholder="Paste the stack trace here...",
        height=150,
        key="bug_stack_trace",
    )

    if st.button("Analyze Bug", type="primary", key="btn_bug"):
        if not description:
            st.error("Please enter a bug description.")
            return

        engine = st.session_state.get("rag_engine")
        if not engine:
            st.warning("RAG engine not initialized.")
            return

        with st.spinner("Analyzing bug..."):
            from src.sdlc.bug_assistant import BugAssistant
            assistant = BugAssistant(
                rag_engine=engine,
                crawler=st.session_state.get("crawler"),
            )
            analysis = assistant.analyze_bug(description, stack_trace)

            st.markdown(f"### Analysis: {analysis.summary}")
            severity_colors = {"critical": "#da1e28", "high": "#da1e28", "medium": "#f1c21b", "low": "#24a148"}
            sev_color = severity_colors.get(analysis.severity.lower(), "#525252")
            sev_text_color = "#161616" if analysis.severity.lower() == "medium" else "#fff"
            st.markdown(f'**Severity:** {render_carbon_tag(analysis.severity, sev_color, sev_text_color)}', unsafe_allow_html=True)

            if analysis.affected_components:
                st.markdown("**Affected Components:**")
                for comp in analysis.affected_components:
                    st.markdown(f"- `{comp}`")

            if analysis.probable_causes:
                st.markdown("### Probable Causes")
                for cause in analysis.probable_causes:
                    st.markdown(
                        f"- **{cause.description}** "
                        f"(confidence: {cause.confidence:.0%}) "
                        f"— `{cause.component}`"
                    )

            if analysis.suggested_fixes:
                st.markdown("### Suggested Fixes")
                risk_colors = {"high": "#da1e28", "medium": "#f1c21b", "low": "#24a148"}
                for fix in analysis.suggested_fixes:
                    r_color = risk_colors.get(fix.risk_level.lower(), "#525252")
                    r_text_color = "#161616" if fix.risk_level.lower() == "medium" else "#fff"
                    st.markdown(
                        f'{render_carbon_tag(fix.risk_level, r_color, r_text_color)} {fix.description}<br/>'
                        f'&nbsp;&nbsp;&nbsp;&nbsp;Location: <code>{fix.code_location}</code>',
                        unsafe_allow_html=True,
                    )

            if analysis.test_cases:
                st.markdown("### Verification Test Cases")
                for tc in analysis.test_cases:
                    with st.expander(tc.name):
                        st.markdown(tc.description)
                        if tc.code:
                            st.code(tc.code, language="csharp")


def _render_test_generator():
    """Test case generator."""
    st.subheader("Test Case Generator")

    component_path = st.text_input(
        "Component File Path",
        placeholder="/path/to/SubmitInvoiceHandler.cs",
        key="test_component_path",
    )

    with st.expander("…or upload a file (PDF / .cs / .md / .txt)", expanded=False):
        uploaded = st.file_uploader(
            "Upload component or spec file",
            type=["cs", "pdf", "md", "txt"],
            key="test_upload",
            accept_multiple_files=False,
        )
        if uploaded is not None:
            staged = stage_uploaded_file(uploaded)
            if staged:
                component_path = staged
                st.success(f"Using uploaded **{uploaded.name}** → `{staged}`")

    test_type = st.radio(
        "Test Type",
        ["Unit Tests", "Integration Tests", "Edge Cases"],
        horizontal=True,
        key="test_type",
    )

    if st.button("Generate Tests", type="primary", key="btn_test"):
        if not component_path:
            st.error("Please enter a component file path.")
            return

        engine = st.session_state.get("rag_engine")
        if not engine:
            st.warning("RAG engine not initialized.")
            return

        with st.spinner("Generating test cases..."):
            from src.sdlc.test_generator import TestCaseGenerator
            generator = TestCaseGenerator(
                rag_engine=engine,
                llm=st.session_state.get("llm"),
            )

            if test_type == "Unit Tests":
                code = generator.generate_unit_tests(component_path)
                st.markdown("### Generated Unit Tests")
                st.code(code, language="csharp")
            elif test_type == "Integration Tests":
                code = generator.generate_integration_tests(component_path)
                st.markdown("### Generated Integration Tests")
                st.code(code, language="csharp")
            else:
                edge_cases = generator.suggest_edge_cases(component_path)
                st.markdown(f"### Edge Cases ({len(edge_cases)})")
                for ec in edge_cases:
                    st.markdown(
                        f"- **{ec.name}**: {ec.description}\n"
                        f"  Input: {ec.input_scenario} | Expected: {ec.expected_behavior}"
                    )


def _render_architecture_validator():
    """Architecture rule validator."""
    st.subheader("Architecture Validator")

    report = st.session_state.get("last_crawl_report")
    if not report:
        st.info("Please crawl a solution first (Solution Crawler page).")
        return

    rules_path = st.text_input(
        "Rules File (YAML)",
        value="architecture_rules/coretax_rules.yaml",
        key="arch_rules_path",
    )

    if st.button("Validate Architecture", type="primary", key="btn_arch"):
        from src.sdlc.architecture_validator import ArchitectureValidator
        from pathlib import Path

        if not Path(rules_path).exists():
            st.warning(f"Rules file not found: {rules_path}. Running with default rules.")
            rules_path = None

        with st.spinner("Validating architecture..."):
            validator = ArchitectureValidator(
                rules_path=rules_path,
                crawl_report=report,
            )
            result = validator.validate()

            # Summary
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Rules Checked", result.total_rules_checked)
            with col2:
                st.metric("Passed", result.passed)
            with col3:
                st.metric("Failed", result.failed)
            with col4:
                st.metric("Warnings", result.warnings)

            # Violations
            if result.violations:
                st.markdown("### Violations")
                for v in result.violations:
                    kind = {"error": "error", "warning": "warning", "info": "info"}.get(v.severity, "info")
                    render_carbon_notification(
                        f"<strong>{v.rule}</strong> &mdash; {v.description}<br/>"
                        f"File: <code>{v.file}</code><br/>Fix: {v.suggested_fix}",
                        kind=kind,
                    )
            else:
                st.success("All architecture rules passed!")
