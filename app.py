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
from src.ui.theme import THEME_CSS, HEADER_HTML

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="Lumen.AI | SDLC Knowledge Engine",
    page_icon="\U0001f9e0",
    layout="wide",
    initial_sidebar_state="expanded",
)

# IBM Carbon-inspired theme (single source of truth in src/ui/theme.py)
st.markdown(THEME_CSS, unsafe_allow_html=True)

# Light gradient header bar
st.markdown(HEADER_HTML, unsafe_allow_html=True)

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
    "Solution Crawler": "crawler",
    "Knowledge Store": "knowledge",
    "RAG Chat": "rag_chat",
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
