"""Solution Crawler page."""

import logging
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Optional

import hashlib

import streamlit as st
from src.ui.components import render_mermaid, render_carbon_tag, render_markdown_with_mermaid
from src.crawler.doc_generator import CrawlDocGenerator
from src.crawler.code_doc_generator import CodeDocGenerator

logger = logging.getLogger(__name__)


def _find_sln_in_dir(root: Path) -> Optional[Path]:
    """Return the first .sln file found under a directory (rglob)."""
    matches = sorted(root.rglob("*.sln"))
    return matches[0] if matches else None


def _extract_uploaded_zip(uploaded_file) -> Optional[Path]:
    """Extract an uploaded ZIP into a temp dir and return the .sln path."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="lumen_upload_"))
    zip_path = tmp_dir / uploaded_file.name
    zip_path.write_bytes(uploaded_file.getvalue())
    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(tmp_dir)
    except zipfile.BadZipFile:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise ValueError("Uploaded file is not a valid ZIP archive.")
    sln = _find_sln_in_dir(tmp_dir)
    if not sln:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise FileNotFoundError("No .sln file found inside the uploaded archive.")
    return sln


def _clone_github_repo(url: str, branch: str = "") -> Path:
    """Shallow-clone a GitHub repo to a temp dir and return the .sln path."""
    tmp_dir = Path(tempfile.mkdtemp(prefix="lumen_gh_"))
    cmd = ["git", "clone", "--depth", "1"]
    if branch.strip():
        cmd += ["--branch", branch.strip()]
    cmd += [url.strip(), str(tmp_dir)]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise RuntimeError(f"git clone failed: {proc.stderr.strip() or proc.stdout.strip()}")
    sln = _find_sln_in_dir(tmp_dir)
    if not sln:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise FileNotFoundError("No .sln file found in the cloned repository.")
    return sln


def render_solution_crawler():
    """Render the solution crawler page."""
    st.header("Solution Crawler")

    crawler = st.session_state.get("crawler")
    pipeline = st.session_state.get("pipeline")

    if not crawler:
        st.warning("Crawler not initialized.")
        return

    # Input — three sources: local path, ZIP upload, or GitHub URL
    src_local, src_upload, src_github = st.tabs(
        ["Local Path", "Upload Solution (ZIP)", "GitHub Repository"]
    )

    sln_path = ""
    source_label = ""

    with src_local:
        local_input = st.text_input(
            "Path to .sln file (or directory containing one)",
            placeholder="/path/to/CoreTax.sln",
            key="sln_path",
        )
        if local_input:
            sln_path = local_input
            source_label = "local path"

    with src_upload:
        uploaded = st.file_uploader(
            "Upload a ZIP archive of your entire .NET solution",
            type=["zip"],
            key="sln_upload",
            help="The ZIP must contain a .sln file (anywhere inside).",
        )
        if uploaded is not None:
            if st.session_state.get("_last_upload_name") != uploaded.name:
                try:
                    with st.spinner(f"Extracting {uploaded.name}..."):
                        extracted_sln = _extract_uploaded_zip(uploaded)
                    st.session_state["_uploaded_sln_path"] = str(extracted_sln)
                    st.session_state["_last_upload_name"] = uploaded.name
                    st.success(f"Extracted: {extracted_sln.name}")
                except Exception as e:
                    st.error(f"Upload failed: {e}")
                    st.session_state["_uploaded_sln_path"] = ""
            if st.session_state.get("_uploaded_sln_path"):
                sln_path = st.session_state["_uploaded_sln_path"]
                source_label = f"uploaded ZIP ({uploaded.name})"
                st.caption(f"Will crawl: `{sln_path}`")

    with src_github:
        gh_url = st.text_input(
            "GitHub repository URL",
            placeholder="https://github.com/owner/repo.git",
            key="gh_url",
        )
        gh_branch = st.text_input(
            "Branch (optional)",
            placeholder="main",
            key="gh_branch",
        )
        if gh_url:
            cache_key = f"{gh_url}@{gh_branch}"
            if st.button("Clone Repository", key="gh_clone_btn"):
                try:
                    with st.spinner(f"Cloning {gh_url}..."):
                        cloned_sln = _clone_github_repo(gh_url, gh_branch)
                    st.session_state["_cloned_sln_path"] = str(cloned_sln)
                    st.session_state["_last_clone_key"] = cache_key
                    st.success(f"Cloned. Found solution: {cloned_sln.name}")
                except Exception as e:
                    st.error(f"Clone failed: {e}")
                    st.session_state["_cloned_sln_path"] = ""
            if (
                st.session_state.get("_cloned_sln_path")
                and st.session_state.get("_last_clone_key") == cache_key
            ):
                sln_path = st.session_state["_cloned_sln_path"]
                source_label = f"GitHub ({gh_url})"
                st.caption(f"Will crawl: `{sln_path}`")

    # Optional Angular front-end path. If left empty, the crawler
    # auto-detects any angular.json under the solution directory (works
    # for monorepos that ship the SPA next to the .sln).
    angular_path = st.text_input(
        "Angular front-end path (optional)",
        placeholder="auto-detect from solution dir, or e.g. /path/to/web-ui",
        key="ng_path",
        help="Leave blank to auto-detect angular.json under the solution directory.",
    )

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
                    report = crawler.crawl(
                        sln_path,
                        progress_callback=progress_cb,
                        angular_path=angular_path or "",
                    )
                    progress_bar.progress(1.0)
                    st.session_state.last_crawl_report = report
                    st.success(
                        f"Crawled {len(report.projects)} projects, "
                        f"{len(report.endpoints)} endpoints, "
                        f"{len(report.consumers)} consumers, "
                        f"{len(report.schedulers)} schedulers, "
                        f"{len(report.ui_components)} UI components"
                    )

                    # Generate documentation
                    try:
                        doc_gen = CrawlDocGenerator(llm=st.session_state.get("llm"))
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

                    # Force a clean re-render so the "No crawl results
                    # yet" info box (left over from the previous render
                    # pass) is replaced by the actual result tabs. Without
                    # this, Streamlit streams the new elements alongside
                    # the stale placeholder and you see both the success
                    # banner AND the empty-state message at once.
                    st.rerun()

                except Exception as e:
                    st.error(f"Crawl failed: {e}")

    with col2:
        if st.button(
            "Ingest to Knowledge Store",
            disabled=not st.session_state.get("last_crawl_report"),
        ):
            if pipeline and st.session_state.last_crawl_report:
                store = st.session_state.get("store")
                before_total = store.get_stats().get("total_chunks", 0) if store else 0
                with st.spinner("Ingesting crawl report..."):
                    chunks = pipeline.ingest_crawl_report(st.session_state.last_crawl_report)
                    after_total = store.get_stats().get("total_chunks", 0) if store else 0
                    delta = after_total - before_total
                    delta_str = (
                        f"+{delta}" if delta > 0
                        else f"{delta}" if delta < 0
                        else "±0 (replaced existing)"
                    )
                    st.success(
                        f"Ingested crawl report: {chunks} chunks for this report. "
                        f"Store total: **{before_total} → {after_total}** ({delta_str}). "
                        f"Note: crawl reports use deterministic doc_ids per service, "
                        f"so re-ingesting the same service replaces its chunks."
                    )
                    st.rerun()

    # Download buttons. File names always include the project (.sln)
    # name plus a MM-DD-YYYY timestamp so multiple runs don't overwrite
    # each other in the user's Downloads folder.
    md_report = st.session_state.get("crawl_md_report")
    pdf_report = st.session_state.get("crawl_pdf_report")
    if md_report or pdf_report:
        st.divider()
        dl_col1, dl_col2, dl_spacer = st.columns([1, 1, 2])
        sln_name = st.session_state.get("last_crawl_report", None)
        file_prefix = "crawl_report"
        if sln_name:
            file_prefix = sln_name.solution.replace("\\", "/").split("/")[-1].replace(".sln", "")
        timestamp = datetime.now().strftime("%m-%d-%Y")
        with dl_col1:
            if md_report:
                st.download_button(
                    label="Download MD Report",
                    data=md_report,
                    file_name=f"{file_prefix}_report_{timestamp}.md",
                    mime="text/markdown",
                )
        with dl_col2:
            if pdf_report:
                st.download_button(
                    label="Download PDF Report",
                    data=pdf_report,
                    file_name=f"{file_prefix}_report_{timestamp}.pdf",
                    mime="application/pdf",
                )

        if md_report:
            with st.expander("Preview Technical Documentation", expanded=False):
                st.caption(
                    f"{len(md_report):,} characters - mermaid diagrams render "
                    "inline below."
                )
                render_markdown_with_mermaid(md_report)

    # ── Code Documentation Generator ──────────────────────────────
    # Doxygen-style per-symbol API reference for every C# and
    # Angular/TypeScript file in the crawled solution. Builds on top of
    # the most recent crawl report so it inherits whatever the user just
    # discovered (local path / ZIP upload / GitHub clone).
    if st.session_state.get("last_crawl_report"):
        st.divider()
        st.subheader("Code Documentation")
        st.caption(
            "Generate Doxygen-style per-symbol API documentation from the C# "
            "and Angular/TypeScript source files discovered above. The "
            "result can be downloaded as MD/PDF and ingested into the RAG "
            "knowledge store."
        )
        cd_col1, cd_col2 = st.columns(2)
        with cd_col1:
            if st.button("Generate Code Documentation", type="primary"):
                with st.spinner("Walking source files and extracting symbols..."):
                    try:
                        cdg = CodeDocGenerator(llm=st.session_state.get("llm"))
                        cd_md = cdg.generate_markdown(st.session_state.last_crawl_report)
                        st.session_state.code_doc_md = cd_md
                        try:
                            cd_pdf = cdg.generate_pdf(cd_md)
                            st.session_state.code_doc_pdf = bytes(cd_pdf)
                        except Exception as pdf_err:
                            logger.warning(f"Code-doc PDF generation failed: {pdf_err}")
                            st.session_state.code_doc_pdf = None
                        st.success(
                            f"Generated {len(cd_md):,} characters of code documentation."
                        )
                    except Exception as e:
                        st.error(f"Code documentation generation failed: {e}")
                        logger.exception("Code-doc generation crashed")
        with cd_col2:
            if st.button(
                "Ingest Code Docs to Knowledge Store",
                disabled=not st.session_state.get("code_doc_md"),
            ):
                if pipeline and st.session_state.get("code_doc_md"):
                    with st.spinner("Ingesting code documentation into RAG store..."):
                        try:
                            sln_label = st.session_state.last_crawl_report.solution
                            doc_id = "codedoc_" + hashlib.md5(
                                sln_label.encode("utf-8")
                            ).hexdigest()
                            chunks = pipeline.store.ingest_document(
                                st.session_state.code_doc_md,
                                {
                                    "source_file": f"{sln_label}_code_doc.md",
                                    "doc_kind": "code_documentation",
                                    "service_name": sln_label.replace(".sln", ""),
                                },
                                doc_id,
                            )
                            st.success(
                                f"Ingested code documentation: {chunks} chunks created."
                            )
                        except Exception as e:
                            st.error(f"Ingest failed: {e}")
                            logger.exception("Code-doc ingest crashed")

        cd_md = st.session_state.get("code_doc_md")
        cd_pdf = st.session_state.get("code_doc_pdf")
        if cd_md or cd_pdf:
            cd_dl1, cd_dl2, _cd_sp = st.columns([1, 1, 2])
            sln_obj = st.session_state.get("last_crawl_report")
            cd_prefix = "code_doc"
            if sln_obj:
                cd_prefix = (
                    sln_obj.solution.replace("\\", "/").split("/")[-1].replace(".sln", "")
                    + "_code_doc"
                )
            cd_ts = datetime.now().strftime("%m-%d-%Y")
            with cd_dl1:
                if cd_md:
                    st.download_button(
                        label="Download Code Doc (MD)",
                        data=cd_md,
                        file_name=f"{cd_prefix}_{cd_ts}.md",
                        mime="text/markdown",
                        key="dl_code_doc_md",
                    )
            with cd_dl2:
                if cd_pdf:
                    st.download_button(
                        label="Download Code Doc (PDF)",
                        data=cd_pdf,
                        file_name=f"{cd_prefix}_{cd_ts}.pdf",
                        mime="application/pdf",
                        key="dl_code_doc_pdf",
                    )

            if cd_md:
                with st.expander("Preview Code Documentation", expanded=False):
                    st.caption(
                        f"{len(cd_md):,} characters - per-symbol API reference "
                        "with function explanations."
                    )
                    render_markdown_with_mermaid(cd_md)

    # Display results
    report = st.session_state.get("last_crawl_report")
    if not report:
        st.info("No crawl results yet. Enter a .sln path and click Crawl.")
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
