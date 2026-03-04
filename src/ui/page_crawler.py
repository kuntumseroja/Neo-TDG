"""Solution Crawler page — supports local paths and GitHub URLs."""

import logging
import streamlit as st
from src.ui.components import render_mermaid, render_carbon_tag
from src.crawler.doc_generator import CrawlDocGenerator
from src.readers.github_reader import GitHubReader

logger = logging.getLogger(__name__)

# Shared GitHub reader instance
_github_reader = GitHubReader()


def render_solution_crawler():
    """Render the solution crawler page."""
    st.header("Solution Crawler")

    crawler = st.session_state.get("crawler")
    pipeline = st.session_state.get("pipeline")

    if not crawler:
        st.warning("Crawler not initialized.")
        return

    # ── Source Input: Local Path or GitHub URL ─────────────────────────────
    source_tab_local, source_tab_github = st.tabs(["📁 Local Path", "🔗 GitHub URL"])

    sln_path = None
    _github_cloned_path = None

    with source_tab_local:
        sln_path_local = st.text_input(
            "Path to .sln file",
            placeholder="/path/to/CoreTax.sln",
            key="sln_path",
        )
        if sln_path_local:
            sln_path = sln_path_local

    with source_tab_github:
        github_url = st.text_input(
            "GitHub Repository URL",
            placeholder="https://github.com/owner/repo",
            key="github_url",
        )
        gh_col1, gh_col2 = st.columns([3, 1])
        with gh_col1:
            github_branch = st.text_input(
                "Branch (optional)",
                placeholder="main",
                key="github_branch",
            )
        with gh_col2:
            st.caption("")  # spacer
            st.caption("")
            shallow_clone = st.checkbox("Shallow clone", value=True, key="shallow_clone")

        if github_url and GitHubReader.is_github_url(github_url):
            if st.button("🔍 Clone Repository", type="primary", key="btn_clone"):
                with st.spinner("Cloning repository..."):
                    clone_status = st.empty()
                    try:
                        cloned_path = _github_reader.clone(
                            github_url,
                            branch=github_branch or None,
                            shallow=shallow_clone,
                            progress_callback=lambda msg: clone_status.text(msg),
                        )
                        st.session_state._github_cloned_path = cloned_path

                        # Show repo summary
                        summary = GitHubReader.get_repo_summary(cloned_path)
                        clone_status.empty()
                        st.success(
                            f"Cloned successfully — {summary['total_files']} files, "
                            f"{summary['sln_count']} .sln, "
                            f"{summary['md_count']} .md"
                        )

                        # Show top file extensions
                        top_exts = list(summary["extensions"].items())[:8]
                        ext_tags = " ".join(
                            render_carbon_tag(f"{ext} ({count})", "#e0e0e0", "#161616")
                            for ext, count in top_exts
                        )
                        st.markdown(ext_tags, unsafe_allow_html=True)

                        # Show discovered .sln files
                        sln_files = GitHubReader.find_solution_files(cloned_path)
                        if sln_files:
                            st.markdown(f"**Found {len(sln_files)} solution file(s):**")
                            for sf in sln_files:
                                st.text(f"  📄 {sf}")
                        else:
                            st.info(
                                "No .sln files found. You can still ingest markdown "
                                "and source files via the Knowledge Store page."
                            )

                    except Exception as e:
                        clone_status.empty()
                        st.error(f"Clone failed: {e}")

        elif github_url:
            st.warning("Please enter a valid GitHub URL (https://github.com/owner/repo)")

        # Use cloned path if available
        _github_cloned_path = st.session_state.get("_github_cloned_path")
        if _github_cloned_path:
            sln_files = GitHubReader.find_solution_files(_github_cloned_path)
            if sln_files:
                selected_sln = st.selectbox(
                    "Select solution to crawl",
                    sln_files,
                    key="selected_sln",
                    format_func=lambda x: x.split("/")[-1],
                )
                sln_path = selected_sln

            # Cleanup button
            if st.button("🗑️ Clear cloned repo", key="btn_cleanup"):
                _github_reader.cleanup(_github_cloned_path)
                st.session_state._github_cloned_path = None
                st.rerun()

    # ── Crawl & Ingest Buttons ────────────────────────────────────────────
    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Crawl Solution", type="primary", disabled=not sln_path):
            with st.spinner("Crawling solution..."):
                progress_bar = st.progress(0)
                status_text = st.empty()

                def progress_cb(current, total, name):
                    progress_bar.progress(current / total if total else 0)
                    status_text.text(f"Processing: {name}")

                try:
                    report = crawler.crawl(sln_path, progress_callback=progress_cb)
                    progress_bar.progress(1.0)
                    st.session_state.last_crawl_report = report
                    st.success(
                        f"Crawled {len(report.projects)} projects, "
                        f"{len(report.endpoints)} endpoints, "
                        f"{len(report.consumers)} consumers, "
                        f"{len(report.schedulers)} schedulers"
                    )

                    # Generate documentation
                    try:
                        doc_gen = CrawlDocGenerator()
                        md_content = doc_gen.generate_markdown(report)
                        st.session_state.crawl_md_report = md_content
                        try:
                            pdf_content = doc_gen.generate_pdf(md_content)
                            st.session_state.crawl_pdf_report = bytes(pdf_content)
                        except Exception as pdf_err:
                            logger.warning(f"PDF generation failed: {pdf_err}")
                            st.session_state.crawl_pdf_report = None
                    except Exception as doc_err:
                        logger.warning(f"Doc generation failed: {doc_err}")
                        st.session_state.crawl_md_report = None
                        st.session_state.crawl_pdf_report = None

                except Exception as e:
                    st.error(f"Crawl failed: {e}")

    with col2:
        if st.button(
            "Ingest to Knowledge Store",
            disabled=not st.session_state.get("last_crawl_report"),
        ):
            if pipeline and st.session_state.last_crawl_report:
                with st.spinner("Ingesting crawl report..."):
                    chunks = pipeline.ingest_crawl_report(st.session_state.last_crawl_report)
                    st.success(f"Ingested crawl report: {chunks} chunks created.")

    # Download buttons
    md_report = st.session_state.get("crawl_md_report")
    pdf_report = st.session_state.get("crawl_pdf_report")
    if md_report or pdf_report:
        st.divider()
        dl_col1, dl_col2, dl_spacer = st.columns([1, 1, 2])
        sln_name = st.session_state.get("last_crawl_report", None)
        file_prefix = "crawl_report"
        if sln_name:
            file_prefix = sln_name.solution.replace("\\", "/").split("/")[-1].replace(".sln", "")
        with dl_col1:
            if md_report:
                st.download_button(
                    label="Download MD Report",
                    data=md_report,
                    file_name=f"{file_prefix}_report.md",
                    mime="text/markdown",
                )
        with dl_col2:
            if pdf_report:
                st.download_button(
                    label="Download PDF Report",
                    data=pdf_report,
                    file_name=f"{file_prefix}_report.pdf",
                    mime="application/pdf",
                )

    # Display results
    report = st.session_state.get("last_crawl_report")
    if not report:
        st.info("No crawl results yet. Enter a .sln path or GitHub URL and click Crawl.")
        return

    st.divider()

    # Result tabs
    tab_projects, tab_endpoints, tab_consumers, tab_schedulers, tab_integrations, tab_data = st.tabs(
        ["Projects", "Endpoints", "Consumers", "Schedulers", "Integrations", "Data Models"]
    )

    with tab_projects:
        st.subheader(f"Projects ({len(report.projects)})")
        for p in report.projects:
            with st.expander(f"{p.name} [{p.layer}]"):
                st.write(f"**Framework:** {p.framework}")
                st.write(f"**Path:** {p.path}")
                if p.references:
                    st.write(f"**References:** {', '.join(p.references)}")
                if p.nuget_packages:
                    st.write("**NuGet Packages:**")
                    for pkg in p.nuget_packages[:20]:
                        st.text(f"  - {pkg.name} {pkg.version}")

        # Dependency graph
        if report.dependency_graph.get("edges"):
            st.subheader("Dependency Graph")
            mermaid_lines = ["graph LR"]
            seen_nodes = set()
            for edge in report.dependency_graph.get("edges", [])[:50]:
                src = edge["source"].replace(" ", "_")[:30]
                tgt = edge["target"].replace(" ", "_")[:30]
                mermaid_lines.append(f"    {src} --> {tgt}")
                seen_nodes.update([src, tgt])
            render_mermaid("\n".join(mermaid_lines))

    with tab_endpoints:
        st.subheader(f"Endpoints ({len(report.endpoints)})")
        if report.endpoints:
            method_colors = {"GET": "#24a148", "POST": "#0f62fe", "PUT": "#f1c21b", "DELETE": "#da1e28", "PATCH": "#8a3ffc"}
            for ep in report.endpoints:
                color = method_colors.get(ep.method.upper(), "#525252")
                text_color = "#161616" if ep.method.upper() in ("PUT",) else "#fff"
                auth_tag = " " + render_carbon_tag("Auth", "#525252") if ep.auth_required else ""
                st.markdown(
                    f'{render_carbon_tag(ep.method, color, text_color)} '
                    f'<code style="font-size:0.875rem;">{ep.route}</code>'
                    f'{auth_tag} '
                    f'<span style="color:#525252;font-size:0.8125rem;">{ep.controller} ({ep.file}:{ep.line})</span>',
                    unsafe_allow_html=True,
                )
        else:
            st.info("No endpoints discovered.")

    with tab_consumers:
        st.subheader(f"Consumers ({len(report.consumers)})")
        if report.consumers:
            for c in report.consumers:
                st.markdown(
                    f"**{c.consumer_class}** consumes `{c.message_type}`"
                    + (f" (queue: {c.queue})" if c.queue else "")
                )
        else:
            st.info("No consumers discovered.")

    with tab_schedulers:
        st.subheader(f"Schedulers ({len(report.schedulers)})")
        if report.schedulers:
            for s in report.schedulers:
                st.markdown(
                    f"**{s.job_name}** — `{s.cron_expression}` — {s.description}"
                )
        else:
            st.info("No scheduled jobs discovered.")

    with tab_integrations:
        st.subheader(f"Integrations ({len(report.integrations)})")
        if report.integrations:
            # Group by type
            type_colors = {"redis": "#da1e28", "rabbitmq": "#f1c21b", "http": "#0f62fe", "grpc": "#8a3ffc", "consul": "#009d9a", "s3": "#24a148"}
            by_type = {}
            for ip in report.integrations:
                by_type.setdefault(ip.type, []).append(ip)
            for itype, ips in sorted(by_type.items()):
                color = type_colors.get(itype.lower(), "#525252")
                text_color = "#161616" if itype.lower() == "rabbitmq" else "#fff"
                st.markdown(
                    f'{render_carbon_tag(itype.upper(), color, text_color)} '
                    f'<span style="font-size:0.875rem;color:#525252;">({len(ips)} connections)</span>',
                    unsafe_allow_html=True,
                )
                for ip in ips:
                    st.markdown(
                        f"&nbsp;&nbsp;&nbsp;&nbsp;{ip.source_service} \u2192 {ip.target} ({ip.contract})"
                    )
        else:
            st.info("No integration points discovered.")

    with tab_data:
        st.subheader(f"Data Models ({len(report.data_models)})")
        if report.data_models:
            for dm in report.data_models:
                st.markdown(
                    f"**{dm.name}** (DbContext: {dm.db_context}) — "
                    f"Props: {', '.join(dm.properties[:5])}"
                )
        else:
            st.info("No data models discovered.")
