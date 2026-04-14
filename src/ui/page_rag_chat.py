"""RAG Chat page — conversational query interface."""

import streamlit as st
from src.ui.components import render_markdown_with_mermaid, render_sources, render_confidence_badge, render_carbon_tag


def render_rag_chat():
    """Render the RAG chat page."""
    st.header("RAG Knowledge Chat")

    engine = st.session_state.get("rag_engine")
    if not engine:
        st.warning("RAG engine not initialized. Please check Ollama connection and knowledge store settings.")
        return

    # Mode selector
    col1, col2 = st.columns([2, 3])
    with col1:
        mode = st.radio(
            "Query Mode",
            ["explain", "find", "trace", "impact", "test"],
            horizontal=True,
            help="explain: detailed explanation | find: locate components | trace: flow tracing | impact: change analysis | test: test suggestions",
        )

    with col2:
        # Metadata filters
        with st.expander("Filters", expanded=False):
            filter_service = st.text_input("Service Name", key="filter_service")
            filter_domain = st.text_input("Probis Domain", key="filter_domain")
            filter_type = st.selectbox(
                "Chunk Type",
                ["", "overview", "architecture", "component", "flow", "dependency", "endpoint", "domain_model"],
                key="filter_type",
            )

    # Build filters dict
    filters = {}
    if filter_service:
        filters["service_name"] = filter_service
    if filter_domain:
        filters["probis_domain"] = filter_domain
    if filter_type:
        filters["chunk_type"] = filter_type

    # Conversation management
    memory = st.session_state.get("memory")
    with st.sidebar:
        st.subheader("Conversations")
        if st.button("New Conversation", use_container_width=True):
            st.session_state.conversation_id = None
            st.session_state.chat_messages = []
            st.rerun()

        if memory:
            conversations = memory.list_conversations(limit=20)
            for conv in conversations:
                title = conv.get("title", "Untitled")[:40]
                count = conv.get("message_count", 0)
                if st.button(
                    f"{title} ({count} msgs)",
                    key=f"conv_{conv['id']}",
                    use_container_width=True,
                ):
                    st.session_state.conversation_id = conv["id"]
                    history = memory.get_history(conv["id"], last_n=50)
                    st.session_state.chat_messages = [
                        {"role": m["role"], "content": m["content"]}
                        for m in history
                    ]
                    st.rerun()

    # Display chat messages
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant":
                render_markdown_with_mermaid(msg["content"])
                # Show sources if available
                if "sources" in msg:
                    render_sources(msg["sources"])
                if "confidence" in msg:
                    render_confidence_badge(msg["confidence"])
            else:
                st.markdown(msg["content"])

    # Chat input
    if prompt := st.chat_input("Ask about the CoreTax codebase..."):
        # Add user message
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate response via the split retrieve→stream→finalize
        # pipeline. The knowledge store is verified good (see
        # tests/test_knowledge_integration.py — 40/40 passing). The
        # latency you feel on local queries is Ollama prompt-eval on
        # CPU, not retrieval. Streaming shows the user *something is
        # happening* immediately via a waiting banner that auto-clears
        # on the first token.
        with st.chat_message("assistant"):
            llm = st.session_state.get("llm")

            # 1. Retrieval + rerank + prompt build (fast, with spinner).
            try:
                with st.spinner("Retrieving context..."):
                    prepared = engine.prepare_query(
                        question=prompt,
                        mode=mode,
                        filters=filters if filters else None,
                        conversation_id=st.session_state.conversation_id,
                    )
            except Exception as e:
                st.error(f"Retrieval failed: {e}")
                return

            # Render sources IMMEDIATELY — the knowledge store already
            # told us what it found. No reason to make the user wait
            # until generation finishes to see which documents were
            # retrieved.
            render_sources(prepared["sources"])
            render_confidence_badge(prepared["confidence"])

            if llm is None:
                st.error(
                    "LLM not initialized. Check Ollama is running "
                    "(`ollama serve`) and the sidebar provider settings."
                )
                return

            # 2. Live token streaming with a waiting banner + blinking
            #    cursor + per-token log markers so slow cold-loads are
            #    visible in logs/streamlit.log.
            import time as _time
            import logging as _lg
            _logger = _lg.getLogger(__name__)

            wait_placeholder = st.empty()
            model_label = getattr(llm, "model", "LLM")
            wait_placeholder.markdown(
                f"⏳ _Generating with `{model_label}`… first token can take "
                f"30-120s on CPU for large models._"
            )
            gen_start = _time.monotonic()
            _logger.info(
                "RAG chat: starting generation with %s (prompt=%d chars, mode=%s)",
                model_label, len(prepared["user_prompt"]), mode,
            )

            stream_placeholder = st.empty()
            accumulated: list[str] = []
            first_token_at: list[float] = []  # mutable closure cell

            def _token_iter():
                stream_fn = getattr(llm, "generate_stream", None)
                produced = False

                if stream_fn is None:
                    # Provider without streaming — blocking fallback.
                    blocking = llm.generate(
                        prepared["user_prompt"], prepared["system_prompt"]
                    )
                    if blocking:
                        yield blocking
                    return

                for chunk in stream_fn(
                    prepared["user_prompt"], prepared["system_prompt"]
                ):
                    if chunk:
                        produced = True
                        yield chunk

                if not produced:
                    _logger.warning(
                        "RAG chat: streaming yielded zero tokens, "
                        "falling back to blocking generate()"
                    )
                    blocking = llm.generate(
                        prepared["user_prompt"], prepared["system_prompt"]
                    )
                    if blocking:
                        yield blocking

            # Throttle UI updates — re-rendering the entire accumulated
            # markdown on every token is O(N²) and makes the stream
            # feel slower the longer the answer gets. Update at most
            # ~10 fps (every 100ms) regardless of token arrival rate.
            last_render = [0.0]  # mutable closure cell
            RENDER_INTERVAL = 0.1  # seconds

            def _render_current():
                stream_placeholder.markdown("".join(accumulated) + " ▌")
                last_render[0] = _time.monotonic()

            try:
                for chunk in _token_iter():
                    if not chunk:
                        continue
                    if not first_token_at:
                        first_token_at.append(_time.monotonic() - gen_start)
                        wait_placeholder.empty()
                        _logger.info(
                            "RAG chat: first token after %.1fs",
                            first_token_at[0],
                        )
                        accumulated.append(chunk)
                        _render_current()
                        continue
                    accumulated.append(chunk)
                    # Only re-render if enough time elapsed since last paint.
                    if _time.monotonic() - last_render[0] >= RENDER_INTERVAL:
                        _render_current()
                # Final paint so the last few tokens appear before
                # the placeholder clears.
                _render_current()
            except Exception as e:
                wait_placeholder.empty()
                stream_placeholder.empty()
                _logger.exception("Streaming failed")
                st.error(f"Error generating response: {e}")
                return
            finally:
                try:
                    wait_placeholder.empty()
                except Exception:
                    pass

            # Clear the streaming draft; the final render replaces it
            # with proper mermaid diagrams.
            stream_placeholder.empty()
            answer = "".join(accumulated).strip()

            _logger.info(
                "RAG chat: generation finished in %.1fs (%d chars, "
                "first-token %.1fs)",
                _time.monotonic() - gen_start,
                len(answer),
                first_token_at[0] if first_token_at else -1.0,
            )

            if not answer:
                st.error(
                    "LLM returned an empty response. The model may be "
                    "cold-loading — try again, or switch to a lighter "
                    "model in config.yaml (e.g. llama3.1:8b or "
                    "llama3.2:3b)."
                )
                return

            # 3. Final mermaid-aware render. Malformed diagrams from
            #    small local models fall back to a code block via
            #    render_mermaid's _looks_like_valid_mermaid guard.
            render_markdown_with_mermaid(answer)

            # Related topics (carbon tag chips)
            if prepared["related_topics"]:
                tags_html = (
                    '<div style="margin-top:8px;display:flex;'
                    'flex-wrap:wrap;gap:4px;">'
                )
                for topic in prepared["related_topics"]:
                    tags_html += render_carbon_tag(topic, "#e0e0e0", "#161616")
                tags_html += '</div>'
                st.markdown(tags_html, unsafe_allow_html=True)

            # 4. Persist to conversation memory + update id.
            try:
                result = engine.finalize_query(prompt, answer, prepared)
                st.session_state.conversation_id = result.conversation_id
            except Exception as e:
                _logger.exception("finalize_query failed")
                st.warning(f"Response shown but not saved to memory: {e}")

            st.session_state.chat_messages.append({
                "role": "assistant",
                "content": answer,
                "sources": [s.model_dump() for s in prepared["sources"]],
                "confidence": prepared["confidence"],
            })
