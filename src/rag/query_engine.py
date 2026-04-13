"""RAG Query Engine: retrieve, rerank, augment, generate."""

import logging
from typing import List, Optional

from src.knowledge.vector_store import VectorKnowledgeStore
from src.models.knowledge import ChunkResult, RAGResponse, SourceReference
from src.models.flow import FlowExplanation
from src.rag.reranker import BM25VectorFusionReranker
from src.rag.prompts import build_rag_prompt
from src.rag.conversation import ConversationMemory

logger = logging.getLogger(__name__)


class RAGQueryEngine:
    """Orchestrates the retrieve-rerank-augment-generate pipeline."""

    def __init__(
        self,
        store: VectorKnowledgeStore,
        llm,  # BaseLLM from TechDocGen
        reranker: Optional[BM25VectorFusionReranker] = None,
        conversation_memory: Optional[ConversationMemory] = None,
        retrieve_top_k: int = 20,
        rerank_top_k: int = 5,
    ):
        self.store = store
        self.llm = llm
        self.reranker = reranker or BM25VectorFusionReranker()
        self.memory = conversation_memory
        self.retrieve_top_k = retrieve_top_k
        self.rerank_top_k = rerank_top_k

    def query(
        self,
        question: str,
        mode: str = "explain",
        filters: dict = None,
        conversation_id: str = None,
    ) -> RAGResponse:
        """
        Full RAG pipeline:
        1. Retrieve top_k from vector store
        2. Rerank to final top_k
        3. Build augmented prompt with context + conversation history
        4. Generate answer via LLM
        5. Parse response for sources, confidence, related topics
        6. Store in conversation memory
        """
        # 1. Retrieve
        retrieved = self.store.query(question, top_k=self.retrieve_top_k, filters=filters)
        logger.info(f"Retrieved {len(retrieved)} chunks for: {question[:80]}...")

        # 2. Rerank
        reranked = self.reranker.rerank(question, retrieved, top_k=self.rerank_top_k)
        logger.info(f"Reranked to {len(reranked)} chunks")

        # 3. Get conversation history
        history = []
        if conversation_id and self.memory:
            history = self.memory.get_history(conversation_id)

        # 4. Build augmented prompt
        system_prompt, user_prompt = build_rag_prompt(
            question=question,
            chunks=reranked,
            history=history,
            mode=mode,
        )

        # 5. Generate via LLM
        try:
            answer = self.llm.generate(user_prompt, system_prompt)
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            answer = f"Error generating response: {e}"

        # 6. Build response
        sources = self._extract_sources(reranked)
        confidence = self._assess_confidence(reranked)
        related = self._extract_related_topics(reranked)
        diagram = self._extract_diagram(answer)

        # 7. Handle conversation memory
        if self.memory:
            if not conversation_id:
                conversation_id = self.memory.create_conversation(title=question[:100])
            self.memory.add_message(conversation_id, "user", question)
            self.memory.add_message(
                conversation_id, "assistant", answer,
                sources=[s.model_dump() for s in sources],
            )

        return RAGResponse(
            answer=answer,
            sources=sources,
            confidence=confidence,
            related_topics=related,
            diagram=diagram,
            mode=mode,
            conversation_id=conversation_id,
        )

    def prepare_query(
        self,
        question: str,
        mode: str = "explain",
        filters: dict = None,
        conversation_id: str = None,
    ) -> dict:
        """Run retrieval + rerank + prompt build WITHOUT calling the LLM.

        Returns a dict with `system_prompt`, `user_prompt`, `sources`,
        `confidence`, `related_topics`, `reranked`, and `conversation_id`
        so the UI can stream tokens from the LLM directly (via
        `llm.generate_stream`) and show retrieved sources/confidence
        immediately — before a single token arrives. Pair with
        `finalize_query()` to persist the full answer to conversation
        memory once streaming completes.
        """
        retrieved = self.store.query(
            question, top_k=self.retrieve_top_k, filters=filters
        )
        logger.info(f"Retrieved {len(retrieved)} chunks for: {question[:80]}...")

        reranked = self.reranker.rerank(
            question, retrieved, top_k=self.rerank_top_k
        )
        logger.info(f"Reranked to {len(reranked)} chunks")

        history = []
        if conversation_id and self.memory:
            history = self.memory.get_history(conversation_id)

        system_prompt, user_prompt = build_rag_prompt(
            question=question,
            chunks=reranked,
            history=history,
            mode=mode,
        )

        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "sources": self._extract_sources(reranked),
            "confidence": self._assess_confidence(reranked),
            "related_topics": self._extract_related_topics(reranked),
            "reranked": reranked,
            "conversation_id": conversation_id,
            "mode": mode,
        }

    def finalize_query(
        self,
        question: str,
        answer: str,
        prepared: dict,
    ) -> RAGResponse:
        """Persist a streamed answer to memory and build a RAGResponse.

        Call this after `prepare_query()` + live streaming the LLM output
        yourself. Handles conversation memory bookkeeping and diagram
        extraction identically to the blocking `query()` path.
        """
        sources = prepared["sources"]
        conversation_id = prepared.get("conversation_id")

        if self.memory:
            if not conversation_id:
                conversation_id = self.memory.create_conversation(
                    title=question[:100]
                )
            self.memory.add_message(conversation_id, "user", question)
            self.memory.add_message(
                conversation_id, "assistant", answer,
                sources=[s.model_dump() for s in sources],
            )

        return RAGResponse(
            answer=answer,
            sources=sources,
            confidence=prepared["confidence"],
            related_topics=prepared["related_topics"],
            diagram=self._extract_diagram(answer),
            mode=prepared["mode"],
            conversation_id=conversation_id,
        )

    def trace_flow(self, entry_point: str, filters: dict = None) -> RAGResponse:
        """Specialized query for flow tracing."""
        question = f"Trace the complete flow starting from {entry_point}"
        return self.query(question, mode="trace", filters=filters)

    def impact_analysis(self, component: str, filters: dict = None) -> RAGResponse:
        """Analyze downstream impact of changing a component."""
        question = f"What would be affected if we change {component}? List all downstream dependencies, consumers, and related components."
        return self.query(question, mode="impact", filters=filters)

    def suggest_tests(self, component: str, filters: dict = None) -> RAGResponse:
        """Generate test suggestions for a component."""
        question = f"What test cases should cover {component}? Include unit tests, integration tests, and edge cases."
        return self.query(question, mode="test", filters=filters)

    def _extract_sources(self, chunks: List[ChunkResult]) -> List[SourceReference]:
        """Extract source references from reranked chunks."""
        seen = set()
        sources = []
        for chunk in chunks:
            source_file = chunk.source_file or chunk.metadata.source_file
            if source_file and source_file not in seen:
                seen.add(source_file)
                sources.append(SourceReference(
                    file_path=source_file,
                    service_name=chunk.metadata.service_name,
                    chunk_type=chunk.metadata.chunk_type,
                    relevance_score=chunk.score,
                ))
        return sources

    def _assess_confidence(self, chunks: List[ChunkResult]) -> str:
        """Assess response confidence based on retrieval scores."""
        if not chunks:
            return "low"
        avg_score = sum(c.score for c in chunks) / len(chunks)
        top_score = chunks[0].score if chunks else 0
        if top_score > 0.8 and avg_score > 0.6:
            return "high"
        elif top_score > 0.5 and avg_score > 0.3:
            return "medium"
        return "low"

    def _extract_related_topics(self, chunks: List[ChunkResult]) -> List[str]:
        """Extract related topics from chunk metadata."""
        topics = set()
        for chunk in chunks:
            if chunk.metadata.service_name:
                topics.add(chunk.metadata.service_name)
            if chunk.metadata.heading_path:
                topics.add(chunk.metadata.heading_path)
        return sorted(topics)[:5]

    @staticmethod
    def _extract_diagram(answer: str) -> Optional[str]:
        """Extract Mermaid diagram from LLM answer if present."""
        import re
        match = re.search(r"```mermaid\s*\n(.*?)```", answer, re.DOTALL)
        return match.group(1).strip() if match else None
