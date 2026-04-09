"""Shared UI components for Streamlit pages — IBM Carbon Design System."""

import re
import streamlit as st


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


def render_mermaid(diagram: str):
    """Render a Mermaid diagram safely."""
    if not diagram or not diagram.strip():
        return

    try:
        from streamlit_mermaid import st_mermaid
        clean = _sanitize_mermaid(diagram)
        st_mermaid(clean, height=400)
    except Exception:
        st.code(diagram, language="mermaid")


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
    """Clean up Mermaid code for rendering."""
    # Remove duplicate participant lines
    lines = code.split("\n")
    seen = set()
    clean_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("participant "):
            name = stripped.split(" ", 1)[1] if " " in stripped else stripped
            if name in seen:
                continue
            seen.add(name)
        clean_lines.append(line)
    return "\n".join(clean_lines)


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
