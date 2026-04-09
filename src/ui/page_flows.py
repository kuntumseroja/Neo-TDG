"""Flow Explorer page — trace flows and explain components."""

import streamlit as st
from src.ui.components import (
    render_mermaid,
    render_markdown_with_mermaid,
    render_carbon_tag,
    stage_uploaded_file,
)


def render_flow_explorer():
    """Render the flow explorer page."""
    st.header("Flow Explorer")

    llm = st.session_state.get("llm")
    store = st.session_state.get("store")
    report = st.session_state.get("last_crawl_report")

    tab_trace, tab_explain = st.tabs(["Trace Flow", "Explain Component"])

    with tab_trace:
        _render_trace_flow(llm, report)

    with tab_explain:
        _render_explain_component(llm, store)


def _render_trace_flow(llm, report):
    """Trace a flow from an entry point."""
    st.subheader("Trace Flow")

    entry_point = st.text_input(
        "Entry Point",
        placeholder="e.g., POST /api/invoice/submit or InvoiceController.Submit",
        key="trace_entry",
    )

    if st.button("Trace Flow", type="primary", key="btn_trace", disabled=not entry_point):
        from src.crawler.flow_explainer import FlowExplainer

        with st.spinner("Tracing flow..."):
            explainer = FlowExplainer(crawl_report=report, llm=llm)
            flow = explainer.explain_flow(entry_point)

            # Display title
            st.subheader(flow.title)

            # Display sequence diagram
            if flow.diagram:
                st.markdown("### Sequence Diagram")
                render_mermaid(flow.diagram)

            # Display steps with Carbon tags
            if flow.steps:
                st.markdown("### Flow Steps")
                type_colors = {
                    "http_entry": "#0f62fe", "command": "#8a3ffc", "handler": "#009d9a",
                    "domain_logic": "#161616", "repository": "#525252", "event": "#f1c21b",
                    "consumer": "#da1e28",
                }
                for step in flow.steps:
                    color = type_colors.get(step.type, "#525252")
                    text_color = "#161616" if step.type == "event" else "#fff"
                    tag = render_carbon_tag(step.type, color, text_color)
                    file_ref = f' <code style="font-size:0.75rem;color:#525252;">{step.file}:{step.line}</code>' if step.file else ""
                    st.markdown(
                        f'{step.order}. {tag} <strong>{step.component}</strong>{file_ref}<br/>'
                        f'<span style="color:#525252;margin-left:24px;font-size:0.875rem;">{step.action}</span>',
                        unsafe_allow_html=True,
                    )

            # Display explanation
            if flow.explanation:
                st.markdown("### Explanation")
                render_markdown_with_mermaid(flow.explanation)

    # If we have a crawl report, show available endpoints
    if report and report.endpoints:
        with st.expander("Available Endpoints (from last crawl)"):
            for ep in report.endpoints[:30]:
                st.text(f"{ep.method} {ep.route} — {ep.controller}")


def _render_explain_component(llm, store):
    """Explain a component."""
    st.subheader("Explain Component")

    col1, col2 = st.columns(2)
    with col1:
        file_path = st.text_input(
            "File Path",
            placeholder="/path/to/MyService.cs",
            key="explain_file",
        )
    with col2:
        component_name = st.text_input(
            "Class/Method Name (optional)",
            placeholder="e.g., InvoiceHandler",
            key="explain_component",
        )

    with st.expander("…or upload a file (PDF / .cs / .md / .txt)", expanded=False):
        uploaded = st.file_uploader(
            "Upload component file",
            type=["cs", "pdf", "md", "txt"],
            key="explain_upload",
            accept_multiple_files=False,
        )
        if uploaded is not None:
            staged = stage_uploaded_file(uploaded)
            if staged:
                file_path = staged
                st.success(f"Using uploaded **{uploaded.name}** → `{staged}`")

    explain_type = st.radio(
        "Explain As",
        ["Class", "Method", "Validation Rules"],
        horizontal=True,
        key="explain_type",
    )

    if st.button("Explain", type="primary", key="btn_explain", disabled=not file_path):
        from src.crawler.component_explainer import ComponentExplainer

        with st.spinner("Generating explanation..."):
            explainer = ComponentExplainer(llm=llm, vector_store=store)

            if explain_type == "Class":
                result = explainer.explain_class(file_path, component_name)
                st.markdown(f"### {result.name} ({result.type})")
                render_markdown_with_mermaid(result.explanation)

                if result.dependencies:
                    st.markdown("**Dependencies:**")
                    for dep in result.dependencies:
                        st.markdown(f"- `{dep}`")
                if result.domain_events:
                    st.markdown("**Domain Events:**")
                    for evt in result.domain_events:
                        st.markdown(f"- `{evt}`")
                if result.business_rules:
                    st.markdown("**Business Rules:**")
                    for rule in result.business_rules:
                        st.markdown(f"- {rule}")

            elif explain_type == "Method":
                if not component_name:
                    st.error("Please enter a method name.")
                    return
                result = explainer.explain_method(file_path, component_name)
                st.markdown(f"### {result.name}")
                render_markdown_with_mermaid(result.explanation)

            elif explain_type == "Validation Rules":
                rules = explainer.explain_validation_rules(file_path)
                if rules:
                    st.markdown(f"### Validation Rules ({len(rules)})")
                    for rule in rules:
                        st.markdown(
                            f"- **{rule.name}** — Field: `{rule.field}` — "
                            f"Condition: `{rule.condition}`"
                        )
                else:
                    st.info("No validation rules found in this file.")
