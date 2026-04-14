"""RAG prompt templates for different query modes."""

SYSTEM_PROMPT = (
    "You are a CoreTax technical assistant. Answer questions about "
    "the CoreTax system architecture, code, and business logic using ONLY "
    "the provided context. If the context doesn't contain enough information, "
    "say so explicitly. Always cite the source file/service in your answer. "
    "Use markdown formatting with code blocks where appropriate."
)

MODE_INSTRUCTIONS = {
    "explain": (
        "Provide a detailed explanation with architecture context. "
        "Include relationships between components and their purpose."
    ),
    "find": (
        "Locate the specific components, files, or patterns requested. "
        "List file paths and relevant code structures."
    ),
    "trace": (
        "Trace the complete flow from trigger to completion, step by step. "
        "Show each component involved in order, including message passing between services. "
        "If possible, output a Mermaid sequence diagram."
    ),
    "impact": (
        "Analyze what would be affected by a change to this component. "
        "List downstream dependencies, consumers, and related test cases. "
        "Assess the risk level (low/medium/high)."
    ),
    "test": (
        "Suggest comprehensive test cases for this component. "
        "Include unit tests, integration tests, and edge cases. "
        "Output test names, descriptions, and xUnit C# skeletons where applicable."
    ),
}


def build_rag_prompt(
    question: str,
    chunks: list,
    history: list = None,
    mode: str = "explain",
) -> tuple:
    """
    Build (system_prompt, user_prompt) for the RAG query.

    Args:
        question: User's question
        chunks: List of ChunkResult objects
        history: List of {'role': str, 'content': str} dicts
        mode: Query mode (explain|find|trace|impact|test)

    Returns:
        Tuple of (system_prompt, user_prompt)
    """
    # Build context block from retrieved chunks.
    # Cap total context to ~6000 chars (~1500 tokens) to leave room for
    # the model to generate a full answer (especially on 8K-context models).
    MAX_CONTEXT_CHARS = int(__import__("os").environ.get("RAG_MAX_CONTEXT_CHARS", 6000))
    context_parts = []
    total_chars = 0
    for i, chunk in enumerate(chunks, 1):
        source = chunk.source_file or chunk.metadata.source_file or "unknown"
        ctype = chunk.metadata.chunk_type if hasattr(chunk.metadata, "chunk_type") else "general"
        part = (
            f"[Source {i}: {source} | Type: {ctype} | Score: {chunk.score:.2f}]\n"
            f"{chunk.content}"
        )
        if total_chars + len(part) > MAX_CONTEXT_CHARS and context_parts:
            break  # stop adding chunks — leave room for output
        context_parts.append(part)
        total_chars += len(part)
    context_block = "\n\n---\n\n".join(context_parts) if context_parts else "(No relevant context found)"

    # Build conversation history block
    history_block = ""
    if history:
        history_lines = []
        for msg in history[-3:]:
            role = msg.get("role", "user").upper()
            content = msg.get("content", "")
            # Truncate long history entries
            if len(content) > 500:
                content = content[:500] + "..."
            history_lines.append(f"{role}: {content}")
        history_block = "\n".join(history_lines)

    # Build mode instruction
    mode_instruction = MODE_INSTRUCTIONS.get(mode, MODE_INSTRUCTIONS["explain"])

    # Assemble user prompt
    parts = [f"CONTEXT:\n{context_block}"]

    if history_block:
        parts.append(f"\nCONVERSATION HISTORY:\n{history_block}")

    parts.append(f"\nMODE: {mode}\nINSTRUCTION: {mode_instruction}")
    parts.append(f"\nUSER QUESTION: {question}")

    user_prompt = "\n".join(parts)

    return SYSTEM_PROMPT, user_prompt
