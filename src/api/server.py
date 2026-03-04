"""FastAPI server for Neo-TDG API."""

import logging
from pathlib import Path

import yaml
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)


def _load_config() -> dict:
    """Load configuration from config.yaml."""
    config_path = Path(__file__).resolve().parent.parent.parent / "config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f) or {}
    return {}


def _init_services(app: FastAPI, config: dict):
    """Initialize shared services and attach to app.state."""
    from src.knowledge.embeddings import create_embedding_provider
    from src.knowledge.vector_store import VectorKnowledgeStore
    from src.rag.query_engine import RAGQueryEngine
    from src.rag.reranker import BM25VectorFusionReranker
    from src.rag.conversation import ConversationMemory
    from src.crawler.solution_crawler import SolutionCrawler
    from src.pipeline.ingestion import DocumentIngestionPipeline

    # Knowledge store
    ks_config = config.get("knowledge_store", {})
    persist_dir = ks_config.get("persist_dir", "./knowledge_base")
    embedding_provider = create_embedding_provider(config)
    store = VectorKnowledgeStore(
        persist_dir=persist_dir,
        embedding_provider=embedding_provider,
        collection_name=ks_config.get("collection_name", "techdocgen_knowledge"),
    )

    # LLM
    try:
        from src.compat import LLMFactory
        llm = LLMFactory.create(config.get("default_llm_provider", "ollama"), config)
    except Exception as e:
        logger.warning(f"LLM initialization failed: {e}. RAG queries will not generate answers.")
        llm = None

    # Reranker
    reranker_config = ks_config.get("reranker", {})
    reranker = BM25VectorFusionReranker(alpha=reranker_config.get("alpha", 0.5))

    # Conversation memory
    memory = ConversationMemory(str(Path(persist_dir) / "conversations.db"))

    # RAG engine
    rag_engine = RAGQueryEngine(
        store=store, llm=llm, reranker=reranker, conversation_memory=memory,
    ) if llm else None

    # Crawler
    crawler = SolutionCrawler(config.get("crawler", {}))

    # Pipeline
    pipeline = DocumentIngestionPipeline(store, config)

    # Attach to app.state
    app.state.config = config
    app.state.store = store
    app.state.rag_engine = rag_engine
    app.state.crawler = crawler
    app.state.pipeline = pipeline
    app.state.memory = memory
    app.state.llm = llm


def create_app(config: dict = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if config is None:
        config = _load_config()

    app = FastAPI(
        title="Neo-TDG API",
        description="TechDocGen RAG Expansion — AI-Powered SDLC Knowledge Engine",
        version="1.0.0",
    )

    # CORS
    api_config = config.get("api", {})
    app.add_middleware(
        CORSMiddleware,
        allow_origins=api_config.get("cors_origins", ["*"]),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Initialize services
    _init_services(app, config)

    # Register routes
    from src.api.routes.query import router as query_router
    from src.api.routes.crawl import router as crawl_router
    from src.api.routes.explain import router as explain_router
    from src.api.routes.knowledge import router as knowledge_router

    app.include_router(query_router, prefix="/api", tags=["Query"])
    app.include_router(crawl_router, prefix="/api", tags=["Crawl"])
    app.include_router(explain_router, prefix="/api", tags=["Explain"])
    app.include_router(knowledge_router, prefix="/api", tags=["Knowledge"])

    # Register WebSocket endpoints
    from src.api.websocket import register_websockets
    register_websockets(app)

    @app.get("/health")
    def health():
        stats = app.state.store.get_stats() if app.state.store else {}
        return {
            "status": "ok",
            "knowledge_store": {
                "total_chunks": stats.get("total_chunks", 0),
                "total_documents": stats.get("total_documents", 0),
            },
            "rag_engine": app.state.rag_engine is not None,
        }

    return app


# Allow running directly: python -m src.api.server
if __name__ == "__main__":
    import uvicorn

    config = _load_config()
    api_config = config.get("api", {})
    app = create_app(config)
    uvicorn.run(
        app,
        host=api_config.get("host", "0.0.0.0"),
        port=api_config.get("port", 8080),
    )
