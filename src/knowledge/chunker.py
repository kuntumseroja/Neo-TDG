"""Document chunking strategies for the knowledge store."""

import re
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

# Chunk type classification keywords
_CHUNK_TYPE_MAP = {
    "overview": ["overview", "introduction", "summary", "about", "description"],
    "architecture": ["architecture", "design", "structure", "layer", "pattern", "clean architecture"],
    "component": ["class", "interface", "component", "controller", "service", "handler", "module"],
    "flow": ["flow", "sequence", "process", "pipeline", "diagram", "interaction"],
    "dependency": ["dependency", "dependencies", "reference", "import", "package", "nuget"],
    "endpoint": ["endpoint", "api", "route", "http", "rest", "controller"],
    "domain_model": ["domain", "aggregate", "entity", "bounded context", "value object",
                     "ddd", "event", "command", "query", "cqrs"],
}


def _classify_chunk_type(heading: str) -> str:
    """Classify a chunk type from its heading text."""
    heading_lower = heading.lower()
    for chunk_type, keywords in _CHUNK_TYPE_MAP.items():
        if any(kw in heading_lower for kw in keywords):
            return chunk_type
    return "general"


def _count_tokens(text: str) -> int:
    """Count tokens using tiktoken (cl100k_base encoding)."""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except ImportError:
        # Fallback: approximate 1 token ≈ 4 characters
        return len(text) // 4


class MarkdownChunker:
    """Splits markdown by ## / ### headers, respecting token limits."""

    def __init__(self, max_tokens: int = 1500, overlap_tokens: int = 200):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def chunk(self, markdown: str, base_metadata: dict = None) -> List[Dict]:
        """
        Split markdown into chunks by headers.

        Returns list of dicts with 'content' and 'metadata' keys.
        """
        base_metadata = base_metadata or {}
        sections = self._split_by_headers(markdown)

        chunks = []
        for heading, content in sections:
            chunk_type = _classify_chunk_type(heading)
            section_text = f"{heading}\n{content}".strip() if heading else content.strip()

            if not section_text:
                continue

            token_count = _count_tokens(section_text)

            if token_count <= self.max_tokens:
                chunks.append({
                    "content": section_text,
                    "metadata": {
                        **base_metadata,
                        "chunk_type": chunk_type,
                        "heading_path": heading.strip("# ").strip(),
                        "token_count": token_count,
                    },
                })
            else:
                # Section too large: split with overlap
                sub_chunks = self._split_with_overlap(section_text)
                for i, sub in enumerate(sub_chunks):
                    sub_tokens = _count_tokens(sub)
                    chunks.append({
                        "content": sub,
                        "metadata": {
                            **base_metadata,
                            "chunk_type": chunk_type,
                            "heading_path": f"{heading.strip('# ').strip()} (part {i + 1})",
                            "token_count": sub_tokens,
                        },
                    })

        return chunks

    def _split_by_headers(self, markdown: str) -> List[tuple]:
        """Split markdown into (heading, content) tuples by ## and ### headers."""
        # Match lines starting with ## or ### (but not #### or deeper)
        pattern = re.compile(r"^(#{2,3}\s+.+)$", re.MULTILINE)
        parts = pattern.split(markdown)

        sections = []
        if parts[0].strip():
            # Content before any heading
            sections.append(("", parts[0]))

        i = 1
        while i < len(parts):
            heading = parts[i] if i < len(parts) else ""
            content = parts[i + 1] if i + 1 < len(parts) else ""
            sections.append((heading, content))
            i += 2

        return sections

    def _split_with_overlap(self, text: str) -> List[str]:
        """Split large text into chunks with token overlap."""
        paragraphs = text.split("\n\n")
        chunks = []
        current_chunk = []
        current_tokens = 0

        for para in paragraphs:
            para_tokens = _count_tokens(para)

            if current_tokens + para_tokens > self.max_tokens and current_chunk:
                chunks.append("\n\n".join(current_chunk))
                # Keep overlap: walk back from end
                overlap_chunk = []
                overlap_tokens = 0
                for p in reversed(current_chunk):
                    p_tokens = _count_tokens(p)
                    if overlap_tokens + p_tokens > self.overlap_tokens:
                        break
                    overlap_chunk.insert(0, p)
                    overlap_tokens += p_tokens
                current_chunk = overlap_chunk
                current_tokens = overlap_tokens

            current_chunk.append(para)
            current_tokens += para_tokens

        if current_chunk:
            chunks.append("\n\n".join(current_chunk))

        return chunks


class FixedSizeChunker:
    """Splits text into fixed-size token chunks with overlap."""

    def __init__(self, max_tokens: int = 1500, overlap_tokens: int = 200):
        self.max_tokens = max_tokens
        self.overlap_tokens = overlap_tokens

    def chunk(self, text: str, base_metadata: dict = None) -> List[Dict]:
        base_metadata = base_metadata or {}
        try:
            import tiktoken
            enc = tiktoken.get_encoding("cl100k_base")
            tokens = enc.encode(text)
        except ImportError:
            # Fallback: character-based splitting
            char_max = self.max_tokens * 4
            char_overlap = self.overlap_tokens * 4
            chunks = []
            start = 0
            while start < len(text):
                end = min(start + char_max, len(text))
                chunks.append({
                    "content": text[start:end],
                    "metadata": {**base_metadata, "chunk_type": "general"},
                })
                start = end - char_overlap if end < len(text) else end
            return chunks

        chunks = []
        start = 0
        while start < len(tokens):
            end = min(start + self.max_tokens, len(tokens))
            chunk_text = enc.decode(tokens[start:end])
            chunks.append({
                "content": chunk_text,
                "metadata": {**base_metadata, "chunk_type": "general"},
            })
            start = end - self.overlap_tokens if end < len(tokens) else end

        return chunks
