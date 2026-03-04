"""Neo-TDG: TechDocGen RAG Expansion — AI-Powered SDLC Knowledge Engine

Streamlit web application for RAG-powered code knowledge querying,
solution crawling, flow tracing, and SDLC acceleration.

Run: streamlit run app.py
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path
_project_root = str(Path(__file__).resolve().parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import logging
import streamlit as st
import yaml
import requests

from src.ui.components import init_session_state

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="Neo-TDG | SDLC Knowledge Engine",
    page_icon="\U0001f9e0",
    layout="wide",
    initial_sidebar_state="expanded",
)

# IBM Carbon Design System CSS
st.markdown("""
<style>
    /* ── Google Fonts: IBM Plex Sans ── */
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

    /* ── Global Reset ── */
    * { border-radius: 0px !important; }
    html, body,
    [class*="st-"]:not([data-testid="stIconMaterial"]) {
        font-family: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    /* ── Typography ── */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'IBM Plex Sans', sans-serif !important;
        color: #161616 !important;
        font-weight: 600 !important;
        letter-spacing: 0.16px;
    }
    h1 { font-size: 1.75rem !important; }
    h2 { font-size: 1.25rem !important; }
    h3 { font-size: 1rem !important; }
    p, li, label, div:not(:has(> [data-testid="stIconMaterial"])) {
        font-family: 'IBM Plex Sans', sans-serif !important;
    }
    span:not([data-testid="stIconMaterial"]) {
        font-family: 'IBM Plex Sans', sans-serif !important;
    }

    /* ── Force Streamlit icon font (highest specificity, must be LAST) ── */
    span[data-testid="stIconMaterial"][data-testid="stIconMaterial"][data-testid="stIconMaterial"] {
        font-family: 'Material Symbols Rounded' !important;
    }

    /* ── Primary Buttons ── */
    .stButton > button {
        background-color: #0f62fe !important;
        color: #ffffff !important;
        border: none !important;
        font-family: 'IBM Plex Sans', sans-serif !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.16px;
        padding: 11px 64px 11px 16px !important;
        min-height: 48px !important;
        transition: background-color 0.15s ease !important;
    }
    .stButton > button:hover {
        background-color: #0353e9 !important;
    }
    .stButton > button:active {
        background-color: #002d9c !important;
    }

    /* ── Secondary / Ghost Buttons ── */
    .stButton > button[kind="secondary"],
    button[data-testid="baseButton-secondary"] {
        background-color: transparent !important;
        color: #0f62fe !important;
        border: 1px solid #0f62fe !important;
    }
    button[data-testid="baseButton-secondary"]:hover {
        background-color: #e5f0ff !important;
    }

    /* ── Download Buttons ── */
    .stDownloadButton > button {
        background-color: #24a148 !important;
        color: #ffffff !important;
        border: none !important;
        font-family: 'IBM Plex Sans', sans-serif !important;
        font-weight: 500 !important;
        min-height: 48px !important;
    }
    .stDownloadButton > button:hover {
        background-color: #198038 !important;
    }

    /* ── Inputs & Selects ── */
    [data-baseweb="input"], [data-baseweb="select"],
    [data-baseweb="textarea"], .stTextInput > div > div,
    .stTextArea > div > div, .stSelectbox > div > div {
        border-radius: 0 !important;
        border: none !important;
        border-bottom: 1px solid #e0e0e0 !important;
        background-color: #f4f4f4 !important;
        font-family: 'IBM Plex Sans', sans-serif !important;
    }
    [data-baseweb="input"]:focus-within, [data-baseweb="select"]:focus-within,
    .stTextInput > div > div:focus-within, .stTextArea > div > div:focus-within {
        border-bottom: 2px solid #0f62fe !important;
        outline: none !important;
        box-shadow: none !important;
    }

    /* ── Tabs (Carbon underline style) ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0 !important;
        border-bottom: 2px solid #e0e0e0 !important;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent !important;
        border: none !important;
        border-bottom: 3px solid transparent !important;
        color: #525252 !important;
        font-family: 'IBM Plex Sans', sans-serif !important;
        font-size: 0.875rem !important;
        font-weight: 500 !important;
        padding: 12px 16px !important;
        margin-bottom: -2px !important;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        color: #161616 !important;
        border-bottom: 3px solid #0f62fe !important;
        font-weight: 600 !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: #161616 !important;
        background-color: #e8e8e8 !important;
    }

    /* ── Metrics (left accent border) ── */
    [data-testid="stMetric"] {
        background-color: #f4f4f4 !important;
        border-left: 4px solid #0f62fe !important;
        padding: 16px !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.75rem !important;
        color: #525252 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.32px !important;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
        font-weight: 600 !important;
        color: #161616 !important;
    }

    /* ── Sidebar (Soft Blue-to-White Gradient) ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #d0e2ff 0%, #e8f0fe 35%, #f5f8ff 70%, #ffffff 100%) !important;
        border-right: 1px solid #d0e2ff !important;
    }
    [data-testid="stSidebar"] * {
        color: #161616 !important;
    }
    [data-testid="stSidebar"] [data-testid="stMetricLabel"],
    [data-testid="stSidebar"] [data-testid="stMetricLabel"] * {
        color: #525252 !important;
    }
    [data-testid="stSidebar"] [data-testid="stMetricValue"],
    [data-testid="stSidebar"] [data-testid="stMetricValue"] * {
        color: #161616 !important;
    }
    [data-testid="stSidebar"] .stButton > button,
    [data-testid="stSidebar"] .stButton > button * {
        background-color: #0f62fe !important;
        color: #ffffff !important;
        width: 100% !important;
    }
    [data-testid="stSidebar"] .stButton > button:hover,
    [data-testid="stSidebar"] .stButton > button:hover * {
        background-color: #0353e9 !important;
    }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #161616 !important;
    }
    [data-testid="stSidebar"] [data-baseweb="input"],
    [data-testid="stSidebar"] .stTextInput > div > div {
        background-color: #ffffff !important;
        border-bottom: 1px solid #a6c8ff !important;
        color: #161616 !important;
    }
    [data-testid="stSidebar"] [data-baseweb="input"]:focus-within {
        border-bottom: 2px solid #0f62fe !important;
    }
    [data-testid="stSidebar"] [data-baseweb="select"],
    [data-testid="stSidebar"] .stSelectbox > div > div {
        background-color: #ffffff !important;
        border-bottom: 1px solid #a6c8ff !important;
        color: #161616 !important;
    }
    [data-testid="stSidebar"] [data-testid="stMetric"] {
        background-color: rgba(255, 255, 255, 0.8) !important;
        border-left: 4px solid #0f62fe !important;
    }

    /* ── Sidebar Radio Navigation ── */
    [data-testid="stSidebar"] .stRadio > div {
        gap: 0 !important;
    }
    [data-testid="stSidebar"] .stRadio > div > label {
        background-color: transparent !important;
        padding: 12px 16px !important;
        margin: 0 !important;
        border-left: 3px solid transparent;
        transition: all 0.15s ease !important;
        color: #161616 !important;
    }
    [data-testid="stSidebar"] .stRadio > div > label:hover {
        background-color: rgba(15, 98, 254, 0.08) !important;
    }
    [data-testid="stSidebar"] .stRadio > div > label[data-checked="true"],
    [data-testid="stSidebar"] .stRadio > div > label:has(input:checked) {
        background-color: rgba(15, 98, 254, 0.1) !important;
        border-left: 3px solid #0f62fe !important;
    }

    /* ── Expanders ── */
    .streamlit-expanderHeader {
        font-family: 'IBM Plex Sans', sans-serif !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        border: 1px solid #e0e0e0 !important;
        background-color: #ffffff !important;
    }
    details {
        border: 1px solid #e0e0e0 !important;
    }

    /* ── Chat Messages ── */
    [data-testid="stChatMessage"] {
        border: 1px solid #e0e0e0 !important;
        padding: 16px !important;
        margin-bottom: 8px !important;
    }
    [data-testid="stChatMessage"][data-testid*="assistant"],
    .stChatMessage:nth-child(even) {
        background-color: #f4f4f4 !important;
    }

    /* ── Progress Bars ── */
    .stProgress > div > div > div {
        background-color: #0f62fe !important;
    }
    .stProgress > div > div {
        background-color: #e0e0e0 !important;
    }

    /* ── Code Blocks (light background, visible text) ── */
    code {
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.8125rem !important;
        color: #161616 !important;
        background-color: #f4f4f4 !important;
        padding: 2px 6px !important;
    }
    pre {
        background-color: #f4f4f4 !important;
        color: #161616 !important;
        padding: 16px !important;
        font-family: 'IBM Plex Mono', monospace !important;
        border: 1px solid #e0e0e0 !important;
    }
    pre code {
        background-color: transparent !important;
        padding: 0 !important;
        color: #161616 !important;
    }
    /* Streamlit code block container */
    [data-testid="stCode"] pre,
    .stCodeBlock pre {
        background-color: #f4f4f4 !important;
        color: #161616 !important;
    }
    [data-testid="stCode"] code,
    .stCodeBlock code {
        color: #161616 !important;
        background-color: transparent !important;
    }

    /* ── Dividers ── */
    hr, [data-testid="stDivider"] {
        border-color: #e0e0e0 !important;
    }

    /* ── Alerts (Success, Error, Warning, Info) ── */
    .stAlert, [data-testid="stAlert"] {
        border-left-width: 4px !important;
        border-left-style: solid !important;
        font-family: 'IBM Plex Sans', sans-serif !important;
    }
    .stSuccess, [data-baseweb="notification"][kind="positive"] {
        border-left-color: #24a148 !important;
        background-color: #defbe6 !important;
    }
    .stError, [data-baseweb="notification"][kind="negative"] {
        border-left-color: #da1e28 !important;
        background-color: #fff1f1 !important;
    }
    .stWarning, [data-baseweb="notification"][kind="warning"] {
        border-left-color: #f1c21b !important;
        background-color: #fef3cd !important;
    }
    .stInfo, [data-baseweb="notification"][kind="info"] {
        border-left-color: #0f62fe !important;
        background-color: #edf5ff !important;
    }

    /* ── Spinner ── */
    .stSpinner > div {
        border-top-color: #0f62fe !important;
    }

    /* ── Sidebar Expander ── */
    [data-testid="stSidebar"] details {
        border: 1px solid #a6c8ff !important;
        background-color: rgba(255, 255, 255, 0.7) !important;
    }
    [data-testid="stSidebar"] .streamlit-expanderHeader {
        background-color: rgba(255, 255, 255, 0.7) !important;
        border: none !important;
        color: #161616 !important;
    }

    /* ── Caption ── */
    .stCaption, [data-testid="stCaption"] {
        font-size: 0.75rem !important;
        color: #525252 !important;
        letter-spacing: 0.32px !important;
        text-transform: uppercase !important;
    }
    [data-testid="stSidebar"] .stCaption,
    [data-testid="stSidebar"] [data-testid="stCaption"] {
        color: #525252 !important;
    }

    /* ── Tooltip / Help ── */
    [data-testid="stTooltipIcon"] {
        color: #525252 !important;
    }

    /* ── Sidebar Status Tags (override sidebar * rule) ── */
    [data-testid="stSidebar"] .neo-status-tag,
    [data-testid="stSidebar"] .neo-status-tag * {
        color: #ffffff !important;
    }
    .neo-status-tag.tag-green {
        background-color: #24a148 !important;
    }
    .neo-status-tag.tag-red {
        background-color: #da1e28 !important;
    }
</style>
""", unsafe_allow_html=True)

# Carbon Header Bar (use <div> not <h1>/<p> — Streamlit strips inline styles from headings)
st.markdown("""
<div style="background:#161616;padding:1rem 1.5rem;margin:-1rem -1rem 1.5rem -1rem;display:flex;align-items:center;gap:1rem;">
    <div style="width:3px;height:32px;background:#0f62fe;flex-shrink:0;"></div>
    <div>
        <div style="color:#ffffff;margin:0;font-size:1.25rem;font-weight:600;font-family:'IBM Plex Sans',sans-serif;letter-spacing:0.16px;">Neo-TDG</div>
        <div style="color:#a8a8a8;margin:4px 0 0 0;font-size:0.75rem;font-family:'IBM Plex Sans',sans-serif;">SDLC Knowledge Engine &mdash; RAG-Powered Code Intelligence for CoreTax</div>
    </div>
</div>
""", unsafe_allow_html=True)

# Initialize session state
init_session_state()


def load_config() -> dict:
    """Load configuration from config.yaml."""
    config_path = Path(__file__).parent / "config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}


def get_ollama_models(base_url: str) -> list:
    """Fetch available Ollama models."""
    try:
        resp = requests.get(f"{base_url}/api/tags", timeout=5)
        resp.raise_for_status()
        models = resp.json().get("models", [])
        return [m["name"] for m in models]
    except Exception:
        return []


def initialize_services(config: dict):
    """Initialize all backend services."""
    if st.session_state.services_initialized:
        return

    try:
        from src.knowledge.embeddings import create_embedding_provider
        from src.knowledge.vector_store import VectorKnowledgeStore
        from src.rag.query_engine import RAGQueryEngine
        from src.rag.reranker import BM25VectorFusionReranker
        from src.rag.conversation import ConversationMemory
        from src.crawler.solution_crawler import SolutionCrawler
        from src.pipeline.ingestion import DocumentIngestionPipeline

        ks_config = config.get("knowledge_store", {})
        persist_dir = ks_config.get("persist_dir", "./knowledge_base")

        # Embedding provider
        embedding_provider = create_embedding_provider(config)

        # Knowledge store
        store = VectorKnowledgeStore(
            persist_dir=persist_dir,
            embedding_provider=embedding_provider,
            collection_name=ks_config.get("collection_name", "techdocgen_knowledge"),
        )
        st.session_state.store = store

        # LLM
        try:
            from src.compat import LLMFactory
            llm = LLMFactory.create(config.get("default_llm_provider", "ollama"), config)
            st.session_state.llm = llm
        except Exception as e:
            logger.warning(f"LLM init failed: {e}")
            llm = None

        # Reranker
        reranker_config = ks_config.get("reranker", {})
        reranker = BM25VectorFusionReranker(alpha=reranker_config.get("alpha", 0.5))

        # Conversation memory
        memory = ConversationMemory(str(Path(persist_dir) / "conversations.db"))
        st.session_state.memory = memory

        # RAG engine
        if llm:
            rag_engine = RAGQueryEngine(
                store=store, llm=llm, reranker=reranker, conversation_memory=memory,
            )
            st.session_state.rag_engine = rag_engine

        # Crawler
        crawler = SolutionCrawler(config.get("crawler", {}))
        st.session_state.crawler = crawler

        # Pipeline
        pipeline = DocumentIngestionPipeline(store, config)
        st.session_state.pipeline = pipeline

        st.session_state.config = config
        st.session_state.services_initialized = True

    except Exception as e:
        logger.error(f"Service initialization failed: {e}")
        st.error(f"Failed to initialize services: {e}")


# Load config
config = load_config()

# Sidebar
with st.sidebar:
    st.title("Settings")

    # Ollama settings
    with st.expander("Ollama Configuration", expanded=False):
        ollama_url = st.text_input(
            "Ollama URL",
            value=config.get("llm_providers", {}).get("ollama", {}).get("base_url", "http://localhost:11434"),
            key="ollama_url",
        )
        # Update config
        config.setdefault("llm_providers", {}).setdefault("ollama", {})["base_url"] = ollama_url

        models = get_ollama_models(ollama_url)
        if models:
            default_model = config.get("llm_providers", {}).get("ollama", {}).get("model", "llama3.2")
            default_idx = models.index(default_model) if default_model in models else 0
            selected_model = st.selectbox("LLM Model", models, index=default_idx, key="ollama_model")
            config["llm_providers"]["ollama"]["model"] = selected_model
        else:
            st.text_input(
                "LLM Model",
                value=config.get("llm_providers", {}).get("ollama", {}).get("model", "llama3.2"),
                key="ollama_model_text",
            )

        # Embedding model
        embed_model = st.text_input(
            "Embedding Model",
            value=config.get("knowledge_store", {}).get("embedding", {}).get("model", "nomic-embed-text"),
            key="embed_model",
        )
        config.setdefault("knowledge_store", {}).setdefault("embedding", {})["model"] = embed_model

    # Knowledge store info
    with st.expander("Knowledge Store", expanded=False):
        persist_dir = st.text_input(
            "Persist Directory",
            value=config.get("knowledge_store", {}).get("persist_dir", "./knowledge_base"),
            key="persist_dir",
        )
        config.setdefault("knowledge_store", {})["persist_dir"] = persist_dir

        if st.session_state.get("store"):
            stats = st.session_state.store.get_stats()
            st.metric("Chunks", stats.get("total_chunks", 0))
            st.metric("Documents", stats.get("total_documents", 0))

    # Initialize services
    if st.button("Initialize / Reconnect", use_container_width=True, type="primary"):
        st.session_state.services_initialized = False
        initialize_services(config)
        st.rerun()

    # Status indicators (Carbon tags)
    st.divider()
    st.caption("Service Status")
    llm_ok = bool(st.session_state.get("llm"))
    store_ok = bool(st.session_state.get("store"))
    _tag_html = '<div style="display:flex;gap:8px;flex-wrap:wrap;">'
    _cls = "tag-green" if llm_ok else "tag-red"
    _l = "LLM Connected" if llm_ok else "LLM Offline"
    _tag_html += f'<span class="neo-status-tag {_cls}" style="padding:4px 12px;font-size:0.75rem;font-family:\'IBM Plex Sans\',sans-serif;display:inline-flex;align-items:center;gap:4px;">{_l}</span>'
    _cls = "tag-green" if store_ok else "tag-red"
    _l = "Store Ready" if store_ok else "Store Offline"
    _tag_html += f'<span class="neo-status-tag {_cls}" style="padding:4px 12px;font-size:0.75rem;font-family:\'IBM Plex Sans\',sans-serif;display:inline-flex;align-items:center;gap:4px;">{_l}</span>'
    _tag_html += '</div>'
    st.markdown(_tag_html, unsafe_allow_html=True)

# Auto-initialize on first load
if not st.session_state.services_initialized:
    initialize_services(config)

# Navigation
PAGES = {
    "RAG Chat": "rag_chat",
    "Knowledge Store": "knowledge",
    "Solution Crawler": "crawler",
    "Flow Explorer": "flows",
    "SDLC Tools": "sdlc",
}

with st.sidebar:
    st.divider()
    selected_page = st.radio("Navigation", list(PAGES.keys()), key="nav_page")

# Render selected page
page_key = PAGES[selected_page]

if page_key == "rag_chat":
    from src.ui.page_rag_chat import render_rag_chat
    render_rag_chat()
elif page_key == "knowledge":
    from src.ui.page_knowledge import render_knowledge_management
    render_knowledge_management()
elif page_key == "crawler":
    from src.ui.page_crawler import render_solution_crawler
    render_solution_crawler()
elif page_key == "flows":
    from src.ui.page_flows import render_flow_explorer
    render_flow_explorer()
elif page_key == "sdlc":
    from src.ui.page_sdlc import render_sdlc_tools
    render_sdlc_tools()
