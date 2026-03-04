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

        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                result = engine.query(
                    question=prompt,
                    mode=mode,
                    filters=filters if filters else None,
                    conversation_id=st.session_state.conversation_id,
                )

                # Update conversation ID
                st.session_state.conversation_id = result.conversation_id

                # Display answer
                render_markdown_with_mermaid(result.answer)

                # Display sources
                render_sources(result.sources)

                # Display confidence
                render_confidence_badge(result.confidence)

                # Show related topics as Carbon tags
                if result.related_topics:
                    tags_html = '<div style="margin-top:8px;display:flex;flex-wrap:wrap;gap:4px;">'
                    for topic in result.related_topics:
                        tags_html += render_carbon_tag(topic, "#e0e0e0", "#161616")
                    tags_html += '</div>'
                    st.markdown(tags_html, unsafe_allow_html=True)

                # Store in chat history
                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "content": result.answer,
                    "sources": [s.model_dump() for s in result.sources],
                    "confidence": result.confidence,
                })
