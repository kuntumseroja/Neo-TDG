"""BM25 + vector score fusion reranker."""

import math
import re
from typing import List
from collections import Counter
from src.models.knowledge import ChunkResult


class BM25VectorFusionReranker:
    """Fuses BM25 lexical scores with vector similarity for reranking."""

    def __init__(self, alpha: float = 0.5, k1: float = 1.5, b: float = 0.75):
        """
        Args:
            alpha: Fusion weight. 0=pure BM25, 1=pure vector. Default 0.5.
            k1: BM25 term frequency saturation parameter.
            b: BM25 length normalization parameter.
        """
        self.alpha = alpha
        self.k1 = k1
        self.b = b

    def rerank(
        self, query: str, chunks: List[ChunkResult], top_k: int = 5
    ) -> List[ChunkResult]:
        """
        Rerank chunks using BM25 + vector score fusion.

        1. Compute BM25 scores for query against chunk contents
        2. Normalize both BM25 and vector scores to [0, 1]
        3. Fused score = alpha * vector_score + (1-alpha) * bm25_score
        4. Return top_k by fused score
        """
        if not chunks:
            return []

        if len(chunks) <= top_k:
            return chunks

        query_terms = self._tokenize(query)
        if not query_terms:
            # No meaningful query terms; sort by vector score only
            chunks.sort(key=lambda c: c.score, reverse=True)
            return chunks[:top_k]

        # Compute BM25 scores
        doc_lengths = [len(self._tokenize(c.content)) for c in chunks]
        avg_dl = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 1
        doc_freqs = self._compute_doc_freqs(query_terms, chunks)
        n_docs = len(chunks)

        bm25_scores = []
        for i, chunk in enumerate(chunks):
            tf_map = self._compute_tf(chunk.content)
            score = 0.0
            dl = doc_lengths[i]
            for term in query_terms:
                tf = tf_map.get(term, 0)
                df = doc_freqs.get(term, 0)
                idf = math.log((n_docs - df + 0.5) / (df + 0.5) + 1)
                tf_norm = (tf * (self.k1 + 1)) / (tf + self.k1 * (1 - self.b + self.b * dl / avg_dl))
                score += idf * tf_norm
            bm25_scores.append(score)

        # Normalize scores to [0, 1]
        vector_scores = [c.score for c in chunks]
        norm_vector = self._min_max_normalize(vector_scores)
        norm_bm25 = self._min_max_normalize(bm25_scores)

        # Fuse scores
        fused = []
        for i, chunk in enumerate(chunks):
            fused_score = self.alpha * norm_vector[i] + (1 - self.alpha) * norm_bm25[i]
            fused.append((chunk, fused_score))

        # Sort by fused score and update chunk scores
        fused.sort(key=lambda x: x[1], reverse=True)
        results = []
        for chunk, fscore in fused[:top_k]:
            chunk.score = fscore
            results.append(chunk)

        return results

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        """Simple whitespace + punctuation tokenizer."""
        return [w.lower() for w in re.findall(r"\w+", text) if len(w) > 1]

    def _compute_tf(self, text: str) -> dict:
        """Compute term frequency map for a document."""
        return dict(Counter(self._tokenize(text)))

    def _compute_doc_freqs(self, query_terms: List[str], chunks: List[ChunkResult]) -> dict:
        """Compute document frequency for each query term."""
        df = Counter()
        for chunk in chunks:
            terms_in_doc = set(self._tokenize(chunk.content))
            for term in query_terms:
                if term in terms_in_doc:
                    df[term] += 1
        return dict(df)

    @staticmethod
    def _min_max_normalize(scores: List[float]) -> List[float]:
        """Normalize scores to [0, 1] range."""
        if not scores:
            return []
        min_s = min(scores)
        max_s = max(scores)
        if max_s == min_s:
            return [0.5] * len(scores)
        return [(s - min_s) / (max_s - min_s) for s in scores]
