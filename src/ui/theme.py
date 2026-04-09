"""IBM Consulting / Carbon-inspired theme for the Streamlit UI.

Single source of truth for color tokens, typography and the global CSS
override block. Imported by ``app.py`` so the theme can be tweaked in one
place. Per-page files use the token constants when they need an inline
color (HTTP method tags, severity badges, etc.).

Design language:
  - Light, modern, sleek (soft-blue + white + gradient washes)
  - IBM Plex Sans Light (300) body, 400 headings, tight letter-spacing
  - Subtle 2–6 px corners (soft, not bubbly)
  - Soft drop shadows in the soft-blue range (no flat slabs)
"""

# ── Color tokens ──────────────────────────────────────────────────────────

# Backgrounds
BG_BASE = "#ffffff"
BG_SOFT = "#f5f8ff"          # cards / panels
BG_TINT = "#eef4ff"          # source citations, secondary panels
BG_GRADIENT = (
    "linear-gradient(180deg,#f8fbff 0%,#ffffff 45%,#f5f8ff 100%)"
)
BG_HEADER_GRADIENT = (
    "linear-gradient(135deg,#ffffff 0%,#f5f8ff 50%,#e8f0fe 100%)"
)
BG_SIDEBAR_GRADIENT = (
    "linear-gradient(180deg,#d0e2ff 0%,#e8f0fe 35%,#f5f8ff 70%,#ffffff 100%)"
)

# Blues
SOFT_BLUE = "#a6c8ff"        # accents, borders, soft fills
BLUE = "#0f62fe"             # primary actions
BLUE_DEEP = "#0043ce"        # hover / active
BLUE_GHOST = "rgba(15,98,254,0.08)"

# Ink
INK = "#161616"              # headings
INK_SOFT = "#525252"         # body / captions
LINE = "#e0e6f0"             # dividers, hairline borders

# Status
GREEN = "#24a148"
RED = "#da1e28"
YELLOW = "#f1c21b"
GREEN_SOFT = "#defbe6"
RED_SOFT = "#fff1f1"
YELLOW_SOFT = "#fef3cd"
BLUE_SOFT = "#edf5ff"

# Radius scale
RADIUS_SM = "2px"            # inputs, tags
RADIUS_MD = "4px"            # cards, buttons
RADIUS_LG = "6px"            # major panels, header bar

# Elevation
SHADOW_SOFT = (
    "0 1px 2px rgba(15,98,254,0.04), 0 4px 16px rgba(15,98,254,0.06)"
)
SHADOW_HOVER = (
    "0 2px 4px rgba(15,98,254,0.06), 0 8px 24px rgba(15,98,254,0.10)"
)

# Typography
FONT_FAMILY = "'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif"
FONT_MONO = "'IBM Plex Mono', 'SF Mono', Menlo, monospace"
FONT_WEIGHT_LIGHT = "300"
FONT_WEIGHT_REGULAR = "400"
FONT_WEIGHT_MEDIUM = "500"
FONT_WEIGHT_SEMIBOLD = "600"


# ── Theme CSS ─────────────────────────────────────────────────────────────

THEME_CSS = f"""
<style>
    /* ── Google Fonts: IBM Plex Sans Light + companions ── */
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

    /* ── Global typography ── */
    html, body,
    [class*="st-"]:not([data-testid="stIconMaterial"]) {{
        font-family: {FONT_FAMILY} !important;
        font-weight: {FONT_WEIGHT_LIGHT};
        color: {INK};
    }}
    p, li, label,
    div:not(:has(> [data-testid="stIconMaterial"])) {{
        font-family: {FONT_FAMILY} !important;
        font-weight: {FONT_WEIGHT_LIGHT};
    }}
    span:not([data-testid="stIconMaterial"]) {{
        font-family: {FONT_FAMILY} !important;
    }}
    h1, h2, h3, h4, h5, h6 {{
        font-family: {FONT_FAMILY} !important;
        color: {INK} !important;
        font-weight: {FONT_WEIGHT_REGULAR} !important;
        letter-spacing: -0.01em;
    }}
    h1 {{ font-size: 1.875rem !important; }}
    h2 {{ font-size: 1.375rem !important; }}
    h3 {{ font-size: 1.0625rem !important; font-weight: {FONT_WEIGHT_MEDIUM} !important; }}

    /* Force Streamlit icon font (must stay after the global font rule) */
    span[data-testid="stIconMaterial"][data-testid="stIconMaterial"][data-testid="stIconMaterial"] {{
        font-family: 'Material Symbols Rounded' !important;
    }}

    /* ── Main canvas: soft white-to-blue wash ── */
    [data-testid="stAppViewContainer"],
    section.main,
    .main .block-container {{
        background: {BG_GRADIENT} !important;
    }}

    /* ── Primary buttons: solid blue, soft shadow, gradient hover ── */
    .stButton > button {{
        background: {BLUE} !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: {RADIUS_MD} !important;
        font-family: {FONT_FAMILY} !important;
        font-size: 0.875rem !important;
        font-weight: {FONT_WEIGHT_MEDIUM} !important;
        letter-spacing: 0.01em;
        padding: 10px 20px !important;
        min-height: 44px !important;
        box-shadow: {SHADOW_SOFT} !important;
        transition: all 0.18s ease !important;
    }}
    .stButton > button:hover {{
        background: linear-gradient(135deg, {BLUE} 0%, {BLUE_DEEP} 100%) !important;
        box-shadow: {SHADOW_HOVER} !important;
        transform: translateY(-1px);
    }}
    .stButton > button:active {{
        background: {BLUE_DEEP} !important;
        transform: translateY(0);
    }}

    /* Secondary / ghost buttons */
    .stButton > button[kind="secondary"],
    button[data-testid="baseButton-secondary"] {{
        background: #ffffff !important;
        color: {BLUE} !important;
        border: 1px solid {SOFT_BLUE} !important;
        box-shadow: none !important;
    }}
    button[data-testid="baseButton-secondary"]:hover {{
        background: {BG_TINT} !important;
        border-color: {BLUE} !important;
    }}

    /* Download buttons */
    .stDownloadButton > button {{
        background: {GREEN} !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: {RADIUS_MD} !important;
        font-family: {FONT_FAMILY} !important;
        font-weight: {FONT_WEIGHT_MEDIUM} !important;
        min-height: 44px !important;
        box-shadow: {SHADOW_SOFT} !important;
    }}
    .stDownloadButton > button:hover {{
        background: #198038 !important;
        box-shadow: {SHADOW_HOVER} !important;
    }}

    /* ── Inputs: light fill, soft-blue underline → deepen on focus ── */
    [data-baseweb="input"], [data-baseweb="select"],
    [data-baseweb="textarea"], .stTextInput > div > div,
    .stTextArea > div > div, .stSelectbox > div > div {{
        border-radius: {RADIUS_SM} !important;
        border: none !important;
        border-bottom: 1px solid {SOFT_BLUE} !important;
        background: #f8fbff !important;
        font-family: {FONT_FAMILY} !important;
        font-weight: {FONT_WEIGHT_LIGHT} !important;
    }}
    [data-baseweb="input"]:focus-within, [data-baseweb="select"]:focus-within,
    .stTextInput > div > div:focus-within, .stTextArea > div > div:focus-within {{
        border-bottom: 2px solid {BLUE} !important;
        outline: none !important;
        box-shadow: none !important;
    }}

    /* ── Tabs (Carbon underline, softened) ── */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0 !important;
        border-bottom: 1px solid {LINE} !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        background: transparent !important;
        border: none !important;
        border-bottom: 2px solid transparent !important;
        color: {INK_SOFT} !important;
        font-family: {FONT_FAMILY} !important;
        font-size: 0.875rem !important;
        font-weight: {FONT_WEIGHT_REGULAR} !important;
        padding: 12px 18px !important;
        margin-bottom: -1px !important;
        border-radius: {RADIUS_SM} {RADIUS_SM} 0 0 !important;
        transition: all 0.18s ease !important;
    }}
    .stTabs [data-baseweb="tab"][aria-selected="true"] {{
        color: {INK} !important;
        border-bottom: 2px solid {BLUE} !important;
        font-weight: {FONT_WEIGHT_MEDIUM} !important;
    }}
    .stTabs [data-baseweb="tab"]:hover {{
        color: {INK} !important;
        background: {BLUE_GHOST} !important;
    }}

    /* ── Metrics: soft white card with gradient accent ── */
    [data-testid="stMetric"] {{
        background: #ffffff !important;
        border: 1px solid {LINE} !important;
        border-radius: {RADIUS_MD} !important;
        padding: 18px 20px !important;
        box-shadow: {SHADOW_SOFT} !important;
        position: relative;
        overflow: hidden;
    }}
    [data-testid="stMetric"]::before {{
        content: "";
        position: absolute;
        top: 0; left: 0; bottom: 0; width: 3px;
        background: linear-gradient(180deg, {BLUE} 0%, {SOFT_BLUE} 100%);
    }}
    [data-testid="stMetricLabel"] {{
        font-size: 0.75rem !important;
        color: {INK_SOFT} !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
        font-weight: {FONT_WEIGHT_MEDIUM} !important;
    }}
    [data-testid="stMetricValue"] {{
        font-size: 1.625rem !important;
        font-weight: {FONT_WEIGHT_REGULAR} !important;
        color: {INK} !important;
        letter-spacing: -0.02em;
    }}

    /* ── Sidebar (soft-blue gradient) ── */
    [data-testid="stSidebar"] {{
        background: {BG_SIDEBAR_GRADIENT} !important;
        border-right: 1px solid {SOFT_BLUE} !important;
    }}
    [data-testid="stSidebar"] * {{
        color: {INK};
    }}
    [data-testid="stSidebar"] [data-testid="stMetricLabel"],
    [data-testid="stSidebar"] [data-testid="stMetricLabel"] * {{
        color: {INK_SOFT} !important;
    }}
    [data-testid="stSidebar"] [data-testid="stMetricValue"],
    [data-testid="stSidebar"] [data-testid="stMetricValue"] * {{
        color: {INK} !important;
    }}
    [data-testid="stSidebar"] .stButton > button,
    [data-testid="stSidebar"] .stButton > button * {{
        background: {BLUE} !important;
        color: #ffffff !important;
        width: 100% !important;
    }}
    [data-testid="stSidebar"] .stButton > button:hover,
    [data-testid="stSidebar"] .stButton > button:hover * {{
        background: linear-gradient(135deg, {BLUE} 0%, {BLUE_DEEP} 100%) !important;
    }}
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {{
        color: {INK} !important;
    }}
    [data-testid="stSidebar"] [data-baseweb="input"],
    [data-testid="stSidebar"] .stTextInput > div > div,
    [data-testid="stSidebar"] [data-baseweb="select"],
    [data-testid="stSidebar"] .stSelectbox > div > div {{
        background: #ffffff !important;
        border-bottom: 1px solid {SOFT_BLUE} !important;
        color: {INK} !important;
    }}
    [data-testid="stSidebar"] [data-baseweb="input"]:focus-within {{
        border-bottom: 2px solid {BLUE} !important;
    }}
    [data-testid="stSidebar"] [data-testid="stMetric"] {{
        background: rgba(255,255,255,0.85) !important;
        border: 1px solid {SOFT_BLUE} !important;
    }}
    [data-testid="stSidebar"] details {{
        border: 1px solid {SOFT_BLUE} !important;
        background: rgba(255,255,255,0.7) !important;
        border-radius: {RADIUS_MD} !important;
    }}
    [data-testid="stSidebar"] .streamlit-expanderHeader {{
        background: rgba(255,255,255,0.7) !important;
        border: none !important;
        color: {INK} !important;
    }}

    /* Sidebar radio nav: soft pill highlight */
    [data-testid="stSidebar"] .stRadio > div {{ gap: 0 !important; }}
    [data-testid="stSidebar"] .stRadio > div > label {{
        background: transparent !important;
        padding: 12px 16px !important;
        margin: 2px 0 !important;
        border-left: 3px solid transparent;
        border-radius: 0 {RADIUS_MD} {RADIUS_MD} 0 !important;
        transition: all 0.18s ease !important;
        color: {INK} !important;
    }}
    [data-testid="stSidebar"] .stRadio > div > label:hover {{
        background: {BLUE_GHOST} !important;
    }}
    [data-testid="stSidebar"] .stRadio > div > label[data-checked="true"],
    [data-testid="stSidebar"] .stRadio > div > label:has(input:checked) {{
        background: rgba(15,98,254,0.10) !important;
        border-left: 3px solid {BLUE} !important;
    }}

    /* ── Expanders ── */
    .streamlit-expanderHeader {{
        font-family: {FONT_FAMILY} !important;
        font-weight: {FONT_WEIGHT_MEDIUM} !important;
        font-size: 0.875rem !important;
        border: 1px solid {LINE} !important;
        background: #ffffff !important;
        border-radius: {RADIUS_MD} !important;
    }}
    details {{
        border: 1px solid {LINE} !important;
        border-radius: {RADIUS_MD} !important;
    }}

    /* ── Chat messages ── */
    [data-testid="stChatMessage"] {{
        border: 1px solid {LINE} !important;
        background: #ffffff !important;
        padding: 16px 18px !important;
        margin-bottom: 10px !important;
        border-radius: {RADIUS_MD} !important;
        box-shadow: {SHADOW_SOFT} !important;
    }}
    [data-testid="stChatMessage"][data-testid*="assistant"],
    .stChatMessage:nth-child(even) {{
        background: {BG_TINT} !important;
    }}

    /* ── Progress bars ── */
    .stProgress > div > div > div {{
        background: linear-gradient(90deg, {BLUE} 0%, {SOFT_BLUE} 100%) !important;
        border-radius: {RADIUS_SM} !important;
    }}
    .stProgress > div > div {{
        background: {LINE} !important;
        border-radius: {RADIUS_SM} !important;
    }}

    /* ── Code blocks ── */
    code {{
        font-family: {FONT_MONO} !important;
        font-size: 0.8125rem !important;
        color: {INK} !important;
        background: {BG_TINT} !important;
        padding: 2px 6px !important;
        border-radius: {RADIUS_SM} !important;
    }}
    pre {{
        background: {BG_SOFT} !important;
        color: {INK} !important;
        padding: 16px !important;
        font-family: {FONT_MONO} !important;
        border: 1px solid {LINE} !important;
        border-radius: {RADIUS_MD} !important;
    }}
    pre code {{
        background: transparent !important;
        padding: 0 !important;
        color: {INK} !important;
    }}
    [data-testid="stCode"] pre,
    .stCodeBlock pre {{
        background: {BG_SOFT} !important;
        color: {INK} !important;
        border-radius: {RADIUS_MD} !important;
    }}

    /* ── Dividers ── */
    hr, [data-testid="stDivider"] {{
        border-color: {LINE} !important;
    }}

    /* ── Alerts ── */
    .stAlert, [data-testid="stAlert"] {{
        border-left-width: 4px !important;
        border-left-style: solid !important;
        border-radius: {RADIUS_MD} !important;
        font-family: {FONT_FAMILY} !important;
    }}
    .stSuccess, [data-baseweb="notification"][kind="positive"] {{
        border-left-color: {GREEN} !important;
        background: {GREEN_SOFT} !important;
    }}
    .stError, [data-baseweb="notification"][kind="negative"] {{
        border-left-color: {RED} !important;
        background: {RED_SOFT} !important;
    }}
    .stWarning, [data-baseweb="notification"][kind="warning"] {{
        border-left-color: {YELLOW} !important;
        background: {YELLOW_SOFT} !important;
    }}
    .stInfo, [data-baseweb="notification"][kind="info"] {{
        border-left-color: {BLUE} !important;
        background: {BLUE_SOFT} !important;
    }}

    /* ── Spinner ── */
    .stSpinner > div {{ border-top-color: {BLUE} !important; }}

    /* ── Caption ── */
    .stCaption, [data-testid="stCaption"] {{
        font-size: 0.75rem !important;
        color: {INK_SOFT} !important;
        letter-spacing: 0.06em !important;
        text-transform: uppercase !important;
    }}
    [data-testid="stSidebar"] .stCaption,
    [data-testid="stSidebar"] [data-testid="stCaption"] {{
        color: {INK_SOFT} !important;
    }}

    /* ── Tooltip ── */
    [data-testid="stTooltipIcon"] {{ color: {INK_SOFT} !important; }}

    /* ── Status pills (rounded, soft pastel) ── */
    .neo-status-tag {{
        border-radius: 12px !important;
        padding: 4px 12px;
        font-size: 0.75rem;
        font-family: {FONT_FAMILY};
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-weight: {FONT_WEIGHT_MEDIUM};
    }}
    [data-testid="stSidebar"] .neo-status-tag,
    [data-testid="stSidebar"] .neo-status-tag * {{
        color: #ffffff !important;
    }}
    .neo-status-tag.tag-green {{ background: {GREEN} !important; }}
    .neo-status-tag.tag-red {{ background: {RED} !important; }}
</style>
"""


# ── Header bar ────────────────────────────────────────────────────────────

HEADER_HTML = f"""
<div style="
    background: {BG_HEADER_GRADIENT};
    padding: 1.25rem 1.75rem;
    margin: -1rem -1rem 1.75rem -1rem;
    display: flex;
    align-items: center;
    gap: 1.25rem;
    border-bottom: 1px solid {SOFT_BLUE};
    box-shadow: {SHADOW_SOFT};
">
    <div style="
        width: 4px;
        height: 40px;
        background: linear-gradient(180deg, {BLUE} 0%, {SOFT_BLUE} 100%);
        border-radius: 2px;
        flex-shrink: 0;
    "></div>
    <div>
        <div style="
            color: {INK};
            margin: 0;
            font-size: 1.5rem;
            font-weight: {FONT_WEIGHT_REGULAR};
            font-family: {FONT_FAMILY};
            letter-spacing: -0.02em;
        ">Neo<span style="color: {BLUE}; font-weight: {FONT_WEIGHT_MEDIUM};">-TDG</span></div>
        <div style="
            color: {INK_SOFT};
            margin: 4px 0 0 0;
            font-size: 0.8125rem;
            font-family: {FONT_FAMILY};
            font-weight: {FONT_WEIGHT_LIGHT};
            letter-spacing: 0.01em;
        ">SDLC Knowledge Engine &mdash; RAG-Powered Code Intelligence for CoreTax</div>
    </div>
</div>
"""
