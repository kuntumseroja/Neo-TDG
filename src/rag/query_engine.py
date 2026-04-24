"""RAG Query Engine: retrieve, rerank, augment, generate."""

import logging
from typing import List, Optional

from src.knowledge.vector_store import VectorKnowledgeStore
from src.models.knowledge import ChunkResult, RAGResponse, SourceReference
from src.models.flow import FlowExplanation
from src.rag.reranker import BM25VectorFusionReranker
from src.rag.prompts import build_rag_prompt
from src.rag.conversation import ConversationMemory
from src.rag import personas as personas_mod
from src.rag import citation_validator as cite_mod

logger = logging.getLogger(__name__)


def _kt_pro_flag(config: Optional[dict], key: str) -> bool:
    """Read a `kt_pro.<key>.enabled` feature flag from a config dict.

    Safe against missing keys, non-dict config, and `None`. Defaults to
    False so the absence of config is equivalent to the flag being off —
    which is the whole point of the KT-Pro flag regime.
    """
    if not isinstance(config, dict):
        return False
    kt = config.get("kt_pro") or {}
    entry = kt.get(key) or {}
    return bool(entry.get("enabled", False))


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
        config: Optional[dict] = None,
    ):
        self.store = store
        self.llm = llm
        self.reranker = reranker or BM25VectorFusionReranker()
        self.memory = conversation_memory
        self.retrieve_top_k = retrieve_top_k
        self.rerank_top_k = rerank_top_k
        # Full config dict — used to read kt_pro.* feature flags and the
        # tenant name. None is equivalent to "all flags off".
        self.config = config or {}

    # --- Phase 1 feature-flag helpers -------------------------------------
    @property
    def _six_personas_on(self) -> bool:
        return _kt_pro_flag(self.config, "six_personas")

    @property
    def _orphan_mode_on(self) -> bool:
        return _kt_pro_flag(self.config, "orphan_mode")

    @property
    def _tenant(self) -> str:
        return (self.config.get("kt_pro") or {}).get("tenant", "CoreTax")

    def _resolve_persona(self, persona: Optional[str]) -> Optional[str]:
        """Normalise the requested persona against the feature-flag state.

        Returns None when six-persona mode is off (so the legacy prompt
        path is used) or when the id is unknown — falling back silently
        avoids breaking older clients that don't send one.
        """
        if not self._six_personas_on:
            return None
        if persona and persona in personas_mod.PERSONAS:
            return persona
        return personas_mod.DEFAULT_PERSONA

    def query(
        self,
        question: str,
        mode: str = "explain",
        filters: dict = None,
        conversation_id: str = None,
        persona: Optional[str] = None,
    ) -> RAGResponse:
        """
        Full RAG pipeline:
        1. Retrieve top_k from vector store
        2. Rerank to final top_k
        3. Build augmented prompt with context + conversation history
        4. Generate answer via LLM
        5. Validate paragraph-level citations (Phase 1); retry once or
           refuse with evidence pointers (orphan mode).
        6. Store in conversation memory
        """
        resolved_persona = self._resolve_persona(persona)

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
            persona=resolved_persona,
            tenant=self._tenant,
        )

        # 5. Generate via LLM
        try:
            answer = self.llm.generate(user_prompt, system_prompt)
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            answer = f"Error generating response: {e}"

        # 5a. Citation validation (Phase 1). Only runs when six_personas
        #     is on — the legacy prompt doesn't promise citations so
        #     validating its output would be noise.
        warnings: list[str] = []
        refusal = None
        if resolved_persona is not None:
            answer, warnings, refusal = self._validate_and_maybe_retry(
                answer=answer,
                question=question,
                persona=resolved_persona,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                reranked=reranked,
            )

        # 6. Build response
        sources = self._extract_sources(reranked)
        confidence = self._assess_confidence(reranked)
        related = self._extract_related_topics(reranked)
        diagram = self._extract_diagram(answer) if not refusal else None

        # 7. Handle conversation memory
        if self.memory:
            if not conversation_id:
                conversation_id = self.memory.create_conversation(title=question[:100])
            self.memory.add_message(
                conversation_id, "user", question, persona=resolved_persona,
            )
            self.memory.add_message(
                conversation_id, "assistant", answer,
                sources=[s.model_dump() for s in sources],
                persona=resolved_persona,
            )

        response = RAGResponse(
            answer=answer,
            sources=sources,
            confidence=confidence,
            related_topics=related,
            diagram=diagram,
            mode=mode,
            conversation_id=conversation_id,
            persona=resolved_persona,
            warnings=warnings,
        )
        if refusal is not None:
            response.refused = True
            response.refusal_reason = refusal.reason
            response.hints = refusal.hints
            response.suggested_prompts = refusal.suggested_prompts
        return response

    # --- Validation helpers -----------------------------------------------
    def _validate_and_maybe_retry(
        self,
        *,
        answer: str,
        question: str,
        persona: str,
        system_prompt: str,
        user_prompt: str,
        reranked: list,
    ):
        """Run the citation validator; retry once; refuse on final failure.

        Returns (answer, warnings, refusal_or_None). When orphan mode is
        off, a failing validation becomes a soft warning (legacy behaviour
        from TASK §1.5). When orphan mode is on and the profile sets
        `refuse_without_evidence`, we replace the answer with a structured
        refusal markdown block and set the third tuple element.
        """
        warnings: list[str] = []
        profile = personas_mod.get(persona)  # type: ignore[arg-type]
        min_ratio = personas_mod.min_ratio_for(
            persona, orphan_mode=self._orphan_mode_on,  # type: ignore[arg-type]
        )

        result = cite_mod.validate(answer, min_ratio=min_ratio)
        if result.ok:
            return answer, warnings, None

        logger.info(
            "Citation validation failed (%d/%d cited, ratio=%.2f, min=%.2f) "
            "— retrying with explicit nudge",
            result.paragraphs_cited, result.paragraphs_total, result.ratio, min_ratio,
        )

        nudge = (
            "\n\nMISSING CITATIONS — the previous draft did not cite every "
            "factual sentence. Re-answer, and ensure each paragraph contains "
            "at least one citation of the form [file.cs:L12-L34] or "
            "[doc §3.2]. Unsupported claims must be removed or hedged."
        )
        try:
            retry_answer = self.llm.generate(user_prompt + nudge, system_prompt)
        except Exception as e:
            logger.warning("Citation retry LLM call failed: %s", e)
            retry_answer = answer  # fall through to refusal branch

        retry_result = cite_mod.validate(retry_answer, min_ratio=min_ratio)
        if retry_result.ok:
            return retry_answer, warnings, None

        # Two failures in a row.
        if self._orphan_mode_on and profile.refuse_without_evidence:
            refusal = cite_mod.build_refusal(reranked, question=question)
            return refusal.to_markdown(), ["refused_insufficient_evidence"], refusal

        # Legacy fallback: surface the answer with a soft warning so the UI
        # can badge it.
        warnings.append("low_citation_rate")
        return retry_answer, warnings, None

    def prepare_query(
        self,
        question: str,
        mode: str = "explain",
        filters: dict = None,
        conversation_id: str = None,
        persona: Optional[str] = None,
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

        resolved_persona = self._resolve_persona(persona)
        system_prompt, user_prompt = build_rag_prompt(
            question=question,
            chunks=reranked,
            history=history,
            mode=mode,
            persona=resolved_persona,
            tenant=self._tenant,
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
            "persona": resolved_persona,
        }

    def finalize_query(
        self,
        question: str,
        answer: str,
        prepared: dict,
    ) -> RAGResponse:
        """Persist a streamed answer to memory and build a RAGResponse.

        Call this after `prepare_query()` + live streaming the LLM output
        yourself. Handles conversation memory bookkeeping, citation
        validation, and diagram extraction identically to the blocking
        `query()` path.
        """
        sources = prepared["sources"]
        conversation_id = prepared.get("conversation_id")
        resolved_persona = prepared.get("persona")

        warnings: list[str] = []
        refusal = None
        if resolved_persona is not None:
            answer, warnings, refusal = self._validate_and_maybe_retry(
                answer=answer,
                question=question,
                persona=resolved_persona,
                system_prompt=prepared["system_prompt"],
                user_prompt=prepared["user_prompt"],
                reranked=prepared["reranked"],
            )

        if self.memory:
            if not conversation_id:
                conversation_id = self.memory.create_conversation(
                    title=question[:100]
                )
            self.memory.add_message(
                conversation_id, "user", question, persona=resolved_persona,
            )
            self.memory.add_message(
                conversation_id, "assistant", answer,
                sources=[s.model_dump() for s in sources],
                persona=resolved_persona,
            )

        response = RAGResponse(
            answer=answer,
            sources=sources,
            confidence=prepared["confidence"],
            related_topics=prepared["related_topics"],
            diagram=self._extract_diagram(answer) if not refusal else None,
            mode=prepared["mode"],
            conversation_id=conversation_id,
            persona=resolved_persona,
            warnings=warnings,
        )
        if refusal is not None:
            response.refused = True
            response.refusal_reason = refusal.reason
            response.hints = refusal.hints
            response.suggested_prompts = refusal.suggested_prompts
        return response

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
