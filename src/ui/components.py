"""Shared UI components for Streamlit pages — IBM Carbon Design System."""

import io
import re
import tempfile
from pathlib import Path

import streamlit as st


def stage_uploaded_file(uploaded_file, allowed_suffixes=(".cs", ".pdf", ".md", ".txt")) -> str:
    """Persist a Streamlit-uploaded file to a temp path and return the path.

    PDFs are text-extracted via pypdf and written as a sibling `.txt` so the
    downstream tools (which expect a readable source file on disk) can ingest
    them just like a code file. Other file types are written through verbatim.
    Returns an empty string if the file cannot be staged.
    """
    if uploaded_file is None:
        return ""

    name = uploaded_file.name
    suffix = Path(name).suffix.lower()
    if suffix not in allowed_suffixes:
        st.error(f"Unsupported file type: {suffix}")
        return ""

    raw = uploaded_file.getvalue()

    if suffix == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            st.error("pypdf is required to upload PDFs. Install with `pip install pypdf`.")
            return ""
        try:
            reader = PdfReader(io.BytesIO(raw))
            pages = []
            for i, page in enumerate(reader.pages, start=1):
                try:
                    text = page.extract_text() or ""
                except Exception:
                    text = ""
                if text.strip():
                    pages.append(f"// --- Page {i} ---\n{text.strip()}")
            extracted = "\n\n".join(pages)
        except Exception as e:
            st.error(f"Failed to extract PDF text: {e}")
            return ""
        if not extracted.strip():
            st.error("No extractable text in PDF (scanned/image-only PDFs need OCR).")
            return ""
        tmp = tempfile.NamedTemporaryFile(
            delete=False, suffix=f"_{Path(name).stem}.txt", mode="w", encoding="utf-8"
        )
        tmp.write(extracted)
        tmp.close()
        return tmp.name

    # Code or text file — write bytes through verbatim
    tmp = tempfile.NamedTemporaryFile(
        delete=False, suffix=f"_{Path(name).stem}{suffix}"
    )
    tmp.write(raw)
    tmp.close()
    return tmp.name


# ── Carbon Design Tokens (re-exported from theme.py for back-compat) ──
from src.ui.theme import (
    BLUE as CARBON_BLUE_60,
    INK as CARBON_GRAY_100,
    INK_SOFT as CARBON_GRAY_70,
    LINE as CARBON_GRAY_20,
    BG_TINT as CARBON_GRAY_10,
    BG_SOFT,
    SOFT_BLUE,
    BLUE_GHOST,
    RED as CARBON_RED_60,
    GREEN as CARBON_GREEN_60,
    YELLOW as CARBON_YELLOW_30,
    FONT_FAMILY as CARBON_FONT,
    RADIUS_SM,
    RADIUS_MD,
    SHADOW_SOFT,
)

CARBON_TEAL_60 = "#009d9a"
CARBON_PURPLE_60 = "#8a3ffc"


def render_carbon_tag(label: str, color: str = CARBON_BLUE_60, text_color: str = "#fff") -> str:
    """Return HTML for an inline Carbon-style tag (does NOT call st.markdown)."""
    return (
        f'<span style="background:{color} !important;color:{text_color} !important;padding:3px 10px;'
        f'font-size:0.75rem;font-family:{CARBON_FONT};font-weight:500;'
        f'display:inline-block;margin:2px 2px;border-radius:10px;">{label}</span>'
    )


def render_carbon_notification(message: str, kind: str = "info"):
    """Render a Carbon inline notification."""
    configs = {
        "info": (CARBON_BLUE_60, "#edf5ff", "\u2139"),
        "success": (CARBON_GREEN_60, "#defbe6", "\u2713"),
        "warning": (CARBON_YELLOW_30, "#fef3cd", "\u26a0"),
        "error": (CARBON_RED_60, "#fff1f1", "\u2715"),
    }
    border_color, bg_color, icon = configs.get(kind, configs["info"])
    st.markdown(
        f'<div style="background:{bg_color};border-left:4px solid {border_color};'
        f'border-radius:{RADIUS_MD};padding:12px 16px;margin:8px 0;'
        f'font-family:{CARBON_FONT};font-size:0.875rem;'
        f'box-shadow:{SHADOW_SOFT};">{icon} {message}</div>',
        unsafe_allow_html=True,
    )


def render_carbon_section_header(title: str, subtitle: str = ""):
    """Render a Carbon-style section header with rule line."""
    html = f'<div style="border-bottom:1px solid {CARBON_GRAY_20};padding-bottom:8px;margin:24px 0 16px 0;">'
    html += f'<h3 style="margin:0;font-size:1.25rem;font-weight:600;color:{CARBON_GRAY_100};font-family:{CARBON_FONT};">{title}</h3>'
    if subtitle:
        html += f'<p style="margin:4px 0 0 0;font-size:0.875rem;color:{CARBON_GRAY_70};font-family:{CARBON_FONT};">{subtitle}</p>'
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def render_mermaid(diagram: str, height: int = None):
    """Render a Mermaid diagram safely.

    Height auto-scales with the number of nodes/lines so big diagrams
    (ER, dependency graphs, sequence flows) don't get clipped to an
    empty box. Pass `height` explicitly to override.
    """
    if not diagram or not diagram.strip():
        return

    clean = _sanitize_mermaid(diagram)
    if not _looks_like_valid_mermaid(clean):
        # Cheap heuristic caught a malformed block (common with small
        # local LLMs). Render as a plain code block with a note so the
        # user knows why there's no rendered diagram — mermaid-js would
        # otherwise paint its "Syntax error in text" sticker, which we
        # can't trap from Python.
        st.caption(
            "_Mermaid block looks malformed — showing source instead. "
            "Try a larger / more capable model for better diagrams._"
        )
        st.code(clean or diagram, language="mermaid")
        return

    try:
        from streamlit_mermaid import st_mermaid
        if height is None:
            line_count = clean.count("\n") + 1
            # ~22px per line, clamped between 320 and 1400
            height = max(320, min(1400, 80 + line_count * 22))
        st_mermaid(clean, height=height)
    except Exception:
        st.code(clean or diagram, language="mermaid")


def render_markdown_with_mermaid(markdown_text: str):
    """Render markdown with embedded Mermaid diagrams."""
    parts = re.split(r"```mermaid\s*\n", markdown_text)

    for i, part in enumerate(parts):
        if i == 0:
            if part.strip():
                st.markdown(part)
        else:
            mermaid_end = part.find("```")
            if mermaid_end >= 0:
                mermaid_code = part[:mermaid_end].strip()
                remaining = part[mermaid_end + 3:]
                render_mermaid(mermaid_code)
                if remaining.strip():
                    st.markdown(remaining)
            else:
                st.code(part, language="mermaid")


def render_sources(sources: list):
    """Render source citations from a RAG response (Carbon structured list)."""
    if not sources:
        return

    with st.expander(f"Sources ({len(sources)})", expanded=False):
        for i, src in enumerate(sources, 1):
            file_path = src.get("file_path", "") if isinstance(src, dict) else src.file_path
            score = src.get("relevance_score", 0) if isinstance(src, dict) else src.relevance_score
            service = src.get("service_name", "") if isinstance(src, dict) else src.service_name
            chunk_type = src.get("chunk_type", "") if isinstance(src, dict) else src.chunk_type

            score_tag = render_carbon_tag(f"{score:.2f}", CARBON_BLUE_60, "#fff")
            type_tag = render_carbon_tag(chunk_type, CARBON_GRAY_10, CARBON_GRAY_100) if chunk_type else ""
            service_info = f'<span style="color:{CARBON_GRAY_70};font-size:0.75rem;">{service}</span>' if service else ""

            st.markdown(
                f'<div style="background:{BG_SOFT};border:1px solid {SOFT_BLUE};'
                f'border-left:3px solid {CARBON_BLUE_60};border-radius:{RADIUS_MD};'
                f'padding:10px 14px;margin:6px 0;font-family:{CARBON_FONT};'
                f'box-shadow:{SHADOW_SOFT};">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;">'
                f'<strong style="font-size:0.875rem;">{i}. {file_path}</strong>'
                f'{score_tag}</div>'
                f'<div style="margin-top:4px;">{service_info} {type_tag}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


def render_confidence_badge(confidence: str):
    """Render a Carbon-style confidence badge."""
    colors = {"high": CARBON_GREEN_60, "medium": CARBON_YELLOW_30, "low": CARBON_RED_60}
    text_colors = {"high": "#fff", "medium": CARBON_GRAY_100, "low": "#fff"}
    color = colors.get(confidence, CARBON_GRAY_70)
    text_color = text_colors.get(confidence, "#fff")
    st.markdown(
        f'<span style="background:{color};color:{text_color};padding:3px 12px;'
        f'font-size:0.75rem;font-family:{CARBON_FONT};font-weight:500;display:inline-block;'
        f'margin:4px 0;border-radius:10px;">{confidence.upper()}</span>',
        unsafe_allow_html=True,
    )


def _sanitize_mermaid(code: str) -> str:
    """Clean up Mermaid code for rendering.

    Small local LLMs (llama3.1:8b, deepseek-coder-v2:16b) often emit
    Mermaid that mermaid-js rejects with "Syntax error in text" because
    of tiny formatting issues: duplicate participant declarations,
    stray leading prose, trailing code-fence markers left from truncated
    streaming, leading whitespace before the diagram type, etc. We try
    to repair the common cases before handing off to st_mermaid.
    """
    if not code:
        return code

    # Strip any leftover fence markers and BOM / zero-width spaces.
    code = code.replace("\ufeff", "").replace("\u200b", "")
    code = re.sub(r"^```(?:mermaid)?\s*", "", code.strip())
    code = re.sub(r"```\s*$", "", code).strip()

    lines = code.split("\n")

    # Drop any leading prose lines before the first diagram-type token.
    diagram_types = (
        "sequenceDiagram", "flowchart", "graph", "classDiagram",
        "stateDiagram", "erDiagram", "gantt", "pie", "journey",
        "mindmap", "timeline", "gitGraph", "quadrantChart",
    )
    start_idx = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if any(stripped.startswith(dt) for dt in diagram_types):
            start_idx = i
            break
    lines = lines[start_idx:]

    # Remove duplicate participant lines (sequenceDiagram).
    seen = set()
    clean_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("participant "):
            name = stripped.split(" ", 1)[1] if " " in stripped else stripped
            if name in seen:
                continue
            seen.add(name)
        # Drop stray "```" or "~~~" fence remnants inside the block.
        if stripped in ("```", "~~~"):
            continue
        clean_lines.append(line)
    return "\n".join(clean_lines).strip()


def _looks_like_valid_mermaid(code: str) -> bool:
    """Cheap heuristic to catch obviously-malformed Mermaid before
    mermaid-js renders its "Syntax error in text" sticker. Not a full
    validator — just rules out the cases we see most often from small
    local models."""
    if not code or not code.strip():
        return False
    stripped = code.strip()
    diagram_types = (
        "sequenceDiagram", "flowchart", "graph", "classDiagram",
        "stateDiagram", "erDiagram", "gantt", "pie", "journey",
        "mindmap", "timeline", "gitGraph", "quadrantChart",
    )
    first_line = stripped.split("\n", 1)[0].strip()
    if not any(first_line.startswith(dt) for dt in diagram_types):
        return False
    # sequenceDiagram without any arrow or message is almost always
    # a truncated/half-generated block.
    if first_line.startswith("sequenceDiagram"):
        body = stripped[len("sequenceDiagram"):]
        if "->>" not in body and "-->>" not in body and "->" not in body:
            return False
    return True


def init_session_state():
    """Initialize all session state variables."""
    defaults = {
        "conversation_id": None,
        "chat_messages": [],
        "rag_engine": None,
        "store": None,
        "pipeline": None,
        "crawler": None,
        "memory": None,
        "llm": None,
        "config": {},
        "last_crawl_report": None,
        "crawl_md_report": None,
        "crawl_pdf_report": None,
        "services_initialized": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
