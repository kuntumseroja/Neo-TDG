"""ChromaDB-backed vector knowledge store."""

import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

import chromadb
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings

from src.knowledge.embeddings import BaseEmbeddingProvider
from src.knowledge.chunker import MarkdownChunker
from src.models.knowledge import ChunkResult, ChunkMetadata

logger = logging.getLogger(__name__)


class _ChromaEmbeddingFunction(EmbeddingFunction):
    """Bridges BaseEmbeddingProvider to ChromaDB's EmbeddingFunction protocol."""

    def __init__(self, provider: BaseEmbeddingProvider):
        self.provider = provider

    def __call__(self, input: Documents) -> Embeddings:
        return self.provider.embed_texts(list(input))


class VectorKnowledgeStore:
    """ChromaDB-backed vector store for documentation chunks."""

    def __init__(
        self,
        persist_dir: str,
        embedding_provider: BaseEmbeddingProvider,
        collection_name: str = "techdocgen_knowledge",
        chunker: Optional[MarkdownChunker] = None,
    ):
        self.persist_dir = persist_dir
        self.embedding_provider = embedding_provider
        self.collection_name = collection_name
        self.chunker = chunker or MarkdownChunker()

        # Ensure persist directory exists
        Path(persist_dir).mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB
        self._client = chromadb.PersistentClient(path=str(Path(persist_dir) / "chroma"))
        self._embedding_fn = _ChromaEmbeddingFunction(embedding_provider)
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            embedding_function=self._embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )

        logger.info(
            f"VectorKnowledgeStore initialized: {self._collection.count()} chunks "
            f"in '{collection_name}' at {persist_dir}"
        )

    def ingest_document(
        self, doc_content: str, metadata: dict, doc_id: str = None
    ) -> int:
        """
        Chunk the document, compute embeddings, store in ChromaDB.
        Returns number of chunks created.
        """
        if not doc_id:
            doc_id = hashlib.md5(doc_content[:500].encode()).hexdigest()

        # Delete existing chunks for this document (for re-indexing)
        self._delete_by_doc_id(doc_id)

        # Chunk the document
        base_meta = {**metadata, "doc_id": doc_id}
        chunks = self.chunker.chunk(doc_content, base_meta)

        if not chunks:
            return 0

        # Prepare for ChromaDB
        ids = []
        documents = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            chunk_id = f"{doc_id}_chunk_{i}"
            ids.append(chunk_id)
            documents.append(chunk["content"])

            # ChromaDB metadata must be flat (str, int, float, bool)
            flat_meta = self._flatten_metadata(chunk["metadata"])
            flat_meta["chunk_index"] = i
            flat_meta["ingested_at"] = datetime.utcnow().isoformat()
            metadatas.append(flat_meta)

        # Batch add to ChromaDB (handles embedding internally)
        batch_size = 100
        for start in range(0, len(ids), batch_size):
            end = min(start + batch_size, len(ids))
            self._collection.add(
                ids=ids[start:end],
                documents=documents[start:end],
                metadatas=metadatas[start:end],
            )

        logger.info(f"Ingested document '{doc_id}': {len(chunks)} chunks")
        return len(chunks)

    def ingest_batch(self, docs: List[tuple]) -> dict:
        """
        Batch ingest: list of (content, metadata) or (content, metadata, doc_id) tuples.
        Returns dict with total_chunks and per-doc counts.
        """
        results = {"total_chunks": 0, "documents": {}}
        for item in docs:
            if len(item) == 3:
                content, metadata, doc_id = item
            else:
                content, metadata = item
                doc_id = None
            count = self.ingest_document(content, metadata, doc_id)
            doc_key = doc_id or metadata.get("source_file", "unknown")
            results["documents"][doc_key] = count
            results["total_chunks"] += count
        return results

    def query(
        self,
        question: str,
        top_k: int = 20,
        filters: dict = None,
    ) -> List[ChunkResult]:
        """
        Query ChromaDB with the question embedding.
        Apply metadata filters (service_name, probis_domain, chunk_type).
        """
        where_filter = self._build_where_filter(filters) if filters else None

        try:
            results = self._collection.query(
                query_texts=[question],
                n_results=min(top_k, self._collection.count() or 1),
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return []

        chunks = []
        if results and results["ids"] and results["ids"][0]:
            for i, chunk_id in enumerate(results["ids"][0]):
                doc = results["documents"][0][i] if results["documents"] else ""
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 1.0

                # ChromaDB returns distance; convert to similarity score
                score = 1.0 - distance  # cosine distance to similarity

                chunks.append(ChunkResult(
                    content=doc,
                    metadata=ChunkMetadata(
                        service_name=meta.get("service_name", ""),
                        probis_domain=meta.get("probis_domain", ""),
                        chunk_type=meta.get("chunk_type", "general"),
                        language=meta.get("language", ""),
                        source_file=meta.get("source_file", ""),
                        heading_path=meta.get("heading_path", ""),
                        doc_id=meta.get("doc_id", ""),
                    ),
                    score=score,
                    source_file=meta.get("source_file", ""),
                    chunk_id=chunk_id,
                ))

        # Sort by score descending
        chunks.sort(key=lambda c: c.score, reverse=True)
        return chunks

    def delete_document(self, doc_id: str) -> bool:
        """Delete all chunks for a given document ID."""
        return self._delete_by_doc_id(doc_id)

    def get_stats(self) -> dict:
        """Return knowledge store statistics."""
        count = self._collection.count()

        # Get unique document IDs and service names
        doc_ids = set()
        services = set()
        chunk_types = {}

        if count > 0:
            try:
                all_meta = self._collection.get(include=["metadatas"])
                for meta in (all_meta.get("metadatas") or []):
                    doc_ids.add(meta.get("doc_id", ""))
                    services.add(meta.get("service_name", ""))
                    ct = meta.get("chunk_type", "general")
                    chunk_types[ct] = chunk_types.get(ct, 0) + 1
            except Exception:
                pass

        return {
            "total_chunks": count,
            "total_documents": len(doc_ids - {""}),
            "services": sorted(services - {""}),
            "chunk_types": chunk_types,
            "collection_name": self.collection_name,
            "persist_dir": self.persist_dir,
        }

    def rebuild_index(self) -> None:
        """Drop and re-create the collection."""
        logger.warning(f"Rebuilding index: dropping collection '{self.collection_name}'")
        self._client.delete_collection(self.collection_name)
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self._embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("Index rebuilt (empty collection created)")

    def get_all_doc_ids(self) -> List[str]:
        """Return all unique document IDs in the store."""
        if self._collection.count() == 0:
            return []
        try:
            all_meta = self._collection.get(include=["metadatas"])
            return sorted(set(
                m.get("doc_id", "") for m in (all_meta.get("metadatas") or [])
            ) - {""})
        except Exception:
            return []

    def _delete_by_doc_id(self, doc_id: str) -> bool:
        """Delete all chunks matching a doc_id."""
        try:
            self._collection.delete(where={"doc_id": doc_id})
            return True
        except Exception as e:
            logger.warning(f"Delete by doc_id '{doc_id}' failed: {e}")
            return False

    def _build_where_filter(self, filters: dict) -> Optional[dict]:
        """Build a ChromaDB where filter from user-friendly filters."""
        conditions = []
        for key in ["service_name", "probis_domain", "chunk_type", "language"]:
            if key in filters and filters[key]:
                conditions.append({key: filters[key]})

        if not conditions:
            return None
        if len(conditions) == 1:
            return conditions[0]
        return {"$and": conditions}

    @staticmethod
    def _flatten_metadata(metadata: dict) -> dict:
        """Flatten metadata to ChromaDB-compatible types (str, int, float, bool)."""
        flat = {}
        for k, v in metadata.items():
            if isinstance(v, (str, int, float, bool)):
                flat[k] = v
            elif isinstance(v, datetime):
                flat[k] = v.isoformat()
            elif v is None:
                flat[k] = ""
            else:
                flat[k] = str(v)
        return flat
