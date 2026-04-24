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

    # Documentation structure selector — controls which template the
    # CrawlDocGenerator uses. Default keeps the original full report;
    # "Architecture Doc" produces an 8-section DDD/Clean-Architecture
    # document (bounded contexts, context map, domain model, events,
    # clean arch diagram, sequence diagrams, event streams, glossary).
    doc_structure_label = st.selectbox(
        "Documentation Structure",
        list(CrawlDocGenerator.STRUCTURES.values()),
        index=0,
        key="doc_structure_select",
        help=(
            "Standard = full crawl report covering every section the "
            "crawler can produce. Architecture Doc = DDD/Clean-Arch "
            "8-section template (bounded contexts → context map → "
            "domain model → events → clean arch → sequence → event "
            "stream → glossary)."
        ),
    )
    # Reverse-lookup the key from the label
    doc_structure_key = next(
        (k for k, v in CrawlDocGenerator.STRUCTURES.items() if v == doc_structure_label),
        "standard",
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

                    # Generate documentation in the user-selected structure
                    try:
                        doc_gen = CrawlDocGenerator(llm=st.session_state.get("llm"))
                        md_content = doc_gen.generate_markdown(
                            report, structure=doc_structure_key
                        )
                        st.session_state.crawl_md_report = md_content
                        st.session_state.crawl_doc_structure = doc_structure_key
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

    # Re-generate doc with the currently selected structure WITHOUT
    # re-crawling — useful when the user wants to switch between
    # Standard and Architecture Doc on an already-crawled solution.
    if st.session_state.get("last_crawl_report"):
        if st.button(
            f"Re-generate Documentation ({doc_structure_label})",
            disabled=(
                st.session_state.get("crawl_doc_structure") == doc_structure_key
                and bool(st.session_state.get("crawl_md_report"))
            ),
            help="Rebuild the doc using the currently selected structure.",
        ):
            with st.spinner(f"Rendering {doc_structure_label}..."):
                try:
                    doc_gen = CrawlDocGenerator(llm=st.session_state.get("llm"))
                    md_content = doc_gen.generate_markdown(
                        st.session_state.last_crawl_report,
                        structure=doc_structure_key,
                    )
                    st.session_state.crawl_md_report = md_content
                    st.session_state.crawl_doc_structure = doc_structure_key
                    try:
                        pdf_content = doc_gen.generate_pdf(md_content)
                        st.session_state.crawl_pdf_report = bytes(pdf_content)
                    except Exception as pdf_err:
                        logger.warning(f"PDF re-gen failed: {pdf_err}")
                        st.session_state.crawl_pdf_report = None
                    st.success(f"Re-generated as {doc_structure_label}.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Re-generation failed: {e}")
                    logger.exception("Doc re-generation crashed")

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
            # Render preview OUTSIDE a collapsed expander — streamlit_mermaid
            # mounts its iframe at 0×0 when the parent is hidden on first
            # render, which produces the "empty diagram" bug users saw
            # when opening the expander. A disclosure via checkbox keeps
            # the option to hide the preview but only mounts the iframe
            # once visible.
            show_preview = st.checkbox(
                "Show Technical Documentation Preview",
                value=True,
                key="show_tech_doc_preview",
            )
            if show_preview:
                st.caption(
                    f"{len(md_report):,} characters - mermaid diagrams render "
                    "inline below."
                )
                render_markdown_with_mermaid(md_report)

    # ── KT Bundle (per-persona DOCX) ──────────────────────────────
    # Gated on kt_pro.docx_bundle.enabled so crawls default to the
    # legacy Markdown output until the flag flips on. Six personas, six
    # downloads; PDF only appears when LibreOffice (soffice) is on PATH.
    cfg = st.session_state.get("config") or {}
    _kt_bundle_enabled = bool(
        ((cfg.get("kt_pro") or {}).get("docx_bundle") or {}).get("enabled")
    )
    if st.session_state.get("last_crawl_report") and _kt_bundle_enabled:
        st.divider()
        st.subheader("KT Bundle (per-persona)")
        st.caption(
            "Generate six polished `.docx` (and optional `.pdf`) — one for "
            "each persona (Architect, Developer, Tester, L1, L2, L3). Every "
            "answer is composed under the matching persona prompt."
        )
        if st.button("Build KT Bundle", type="primary", key="build_kt_bundle"):
            with st.spinner("Composing six persona documents — this can take a while..."):
                try:
                    from src.crawler.persona_composer import compose_all
                    from src.ops import sandbox as _sandbox

                    tenant = (cfg.get("kt_pro") or {}).get("tenant", "CoreTax")
                    out_dir = _sandbox.context().paths.knowledge_root.parent / "kt_bundles" / "ui"
                    produced = compose_all(
                        report=st.session_state.last_crawl_report,
                        validation=st.session_state.get("last_validation_report"),
                        tenant=tenant,
                        out_dir=str(out_dir),
                        rag_engine=st.session_state.get("rag_engine"),
                    )
                    st.session_state["_kt_bundle_paths"] = [str(p) for p in produced]
                    st.success(f"Produced {len(produced)} artefact(s).")
                except Exception as e:
                    st.error(f"KT bundle build failed: {e}")
                    logger.exception("KT bundle build crashed")

        artefacts = st.session_state.get("_kt_bundle_paths") or []
        if artefacts:
            docx_paths = [Path(p) for p in artefacts if p.endswith(".docx")]
            pdf_paths = [Path(p) for p in artefacts if p.endswith(".pdf")]
            st.caption(
                f"{len(docx_paths)} DOCX"
                + (f" · {len(pdf_paths)} PDF" if pdf_paths else " · PDF skipped (LibreOffice not on PATH)")
            )
            # 2x3 grid of DOCX downloads. PDF sits under its DOCX when
            # present so users see the pair together.
            cols = st.columns(3)
            for i, dp in enumerate(docx_paths):
                with cols[i % 3]:
                    persona_label = dp.stem.split("_")[-2] if "_" in dp.stem else dp.stem
                    st.markdown(f"**{persona_label.upper()}**")
                    try:
                        st.download_button(
                            f"DOCX ({dp.stat().st_size // 1024} KB)",
                            data=dp.read_bytes(),
                            file_name=dp.name,
                            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                            key=f"dl_bundle_docx_{i}",
                        )
                    except Exception as ex:
                        st.caption(f"unavailable: {ex}")
                    # Match PDF by stem
                    pdf = next((p for p in pdf_paths if p.stem == dp.stem), None)
                    if pdf and pdf.exists():
                        st.download_button(
                            "PDF",
                            data=pdf.read_bytes(),
                            file_name=pdf.name,
                            mime="application/pdf",
                            key=f"dl_bundle_pdf_{i}",
                        )

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
                show_cd_preview = st.checkbox(
                    "Show Code Documentation Preview",
                    value=True,
                    key="show_code_doc_preview",
                )
                if show_cd_preview:
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
