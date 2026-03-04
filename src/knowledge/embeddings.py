"""Embedding provider abstraction for air-gapped operation."""

from abc import ABC, abstractmethod
from typing import List
import logging
import requests

logger = logging.getLogger(__name__)


class BaseEmbeddingProvider(ABC):
    """Abstract embedding provider."""

    @abstractmethod
    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of texts. Returns list of float vectors."""
        pass

    @abstractmethod
    def embed_query(self, query: str) -> List[float]:
        """Embed a single query string."""
        pass

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the embedding dimension."""
        pass


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """Uses Ollama's embedding endpoint with nomic-embed-text."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._dimension: int | None = None

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed a batch of texts via Ollama API."""
        if not texts:
            return []

        url = f"{self.base_url}/api/embed"
        try:
            response = requests.post(
                url,
                json={"model": self.model, "input": texts},
                timeout=120,
            )
            response.raise_for_status()
            result = response.json()
            embeddings = result.get("embeddings", [])
            if embeddings and self._dimension is None:
                self._dimension = len(embeddings[0])
            return embeddings
        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                f"Could not connect to Ollama at {self.base_url}. "
                "Make sure Ollama is running and the embedding model is pulled."
            )
        except Exception as e:
            # Fallback: try the older /api/embeddings endpoint (one at a time)
            logger.warning(f"Batch embed failed ({e}), falling back to single embed")
            return [self._embed_single(text) for text in texts]

    def _embed_single(self, text: str) -> List[float]:
        """Embed a single text via the older /api/embeddings endpoint."""
        url = f"{self.base_url}/api/embeddings"
        response = requests.post(
            url,
            json={"model": self.model, "prompt": text},
            timeout=60,
        )
        response.raise_for_status()
        result = response.json()
        embedding = result.get("embedding", [])
        if embedding and self._dimension is None:
            self._dimension = len(embedding)
        return embedding

    def embed_query(self, query: str) -> List[float]:
        return self.embed_texts([query])[0]

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            # Probe with a dummy text to discover dimension
            self.embed_texts(["dimension probe"])
        return self._dimension or 768


class SentenceTransformerEmbeddingProvider(BaseEmbeddingProvider):
    """Uses sentence-transformers for local embeddings (fallback)."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError(
                "sentence-transformers is required for SentenceTransformerEmbeddingProvider. "
                "Install with: pip install sentence-transformers"
            )
        self.model = SentenceTransformer(model_name)
        self._dimension = self.model.get_sentence_embedding_dimension()

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []
        embeddings = self.model.encode(texts, show_progress_bar=False)
        return [e.tolist() for e in embeddings]

    def embed_query(self, query: str) -> List[float]:
        return self.embed_texts([query])[0]

    @property
    def dimension(self) -> int:
        return self._dimension


def create_embedding_provider(config: dict) -> BaseEmbeddingProvider:
    """Factory function to create the configured embedding provider."""
    embedding_config = config.get("knowledge_store", {}).get("embedding", {})
    provider = embedding_config.get("provider", "ollama")

    if provider == "ollama":
        base_url = config.get("llm_providers", {}).get("ollama", {}).get(
            "base_url", "http://localhost:11434"
        )
        model = embedding_config.get("model", "nomic-embed-text")
        return OllamaEmbeddingProvider(base_url=base_url, model=model)
    elif provider == "sentence-transformers":
        model = embedding_config.get("model", "all-MiniLM-L6-v2")
        return SentenceTransformerEmbeddingProvider(model_name=model)
    else:
        raise ValueError(f"Unknown embedding provider: {provider}")
