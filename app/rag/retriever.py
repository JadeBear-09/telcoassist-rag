from __future__ import annotations

import math
import re
from collections import defaultdict

from app.config import Settings
from app.ingestion.embedder import Embedder
from app.ingestion.indexer import LocalChunkRepository, LocalVectorIndex, QdrantVectorIndex
from app.models import DocumentChunk, RequestIdentity, RetrievalCandidate
from app.security.acl import chunk_allowed_for_identity

TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]+")


class HybridRetriever:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.embedder = Embedder(
            provider=settings.embedding_provider,
            model_name=settings.embedding_model,
            dim=settings.embedding_dim,
        )
        self.repository = LocalChunkRepository(settings.processed_dir)
        self.chunks = self.repository.read_chunks()
        self.embeddings = self.repository.read_embeddings()
        self.keyword = KeywordIndex(self.chunks)
        self.vector = self._build_vector_index()

    def retrieve(
        self,
        question: str,
        top_k: int,
        filters: dict[str, str] | None = None,
        candidate_k: int | None = None,
        identity: RequestIdentity | None = None,
    ) -> list[RetrievalCandidate]:
        candidate_limit = candidate_k or self.settings.candidate_k
        if not self.chunks:
            return []

        query_vector = self.embedder.embed_query(question)
        vector_results = self.vector.search(query_vector, candidate_limit, filters, identity)
        keyword_results = self.keyword.search(question, candidate_limit, filters or {}, identity)
        return reciprocal_rank_fusion(vector_results, keyword_results, top_k=candidate_limit)

    def _build_vector_index(self):
        if self.settings.use_qdrant:
            try:
                return QdrantVectorIndex(
                    url=self.settings.qdrant_url,
                    collection=self.settings.qdrant_collection,
                    vector_size=self.settings.embedding_dim,
                )
            except Exception:
                pass
        return LocalVectorIndex(self.chunks, self.embeddings)


class KeywordIndex:
    def __init__(self, chunks: list[DocumentChunk]) -> None:
        self.chunks = chunks
        self.tokenized = [_tokenize(chunk.text) for chunk in chunks]
        self._bm25 = None
        try:
            from rank_bm25 import BM25Okapi

            self._bm25 = BM25Okapi(self.tokenized)
        except Exception:
            self._idf = _idf(self.tokenized)

    def search(
        self,
        question: str,
        limit: int,
        filters: dict[str, str],
        identity: RequestIdentity | None = None,
    ) -> list[RetrievalCandidate]:
        if not self.chunks:
            return []
        query_tokens = _tokenize(question)
        if self._bm25 is not None:
            scores = self._bm25.get_scores(query_tokens)
        else:
            scores = [_lexical_score(query_tokens, tokens, self._idf) for tokens in self.tokenized]

        candidates: list[RetrievalCandidate] = []
        for chunk, score in zip(self.chunks, scores, strict=True):
            if not _metadata_matches(chunk, filters):
                continue
            if not chunk_allowed_for_identity(chunk, identity):
                continue
            normalized = float(score) / (float(score) + 4.0) if score > 0 else 0.0
            candidates.append(
                RetrievalCandidate(chunk=chunk, score=normalized, keyword_score=normalized)
            )
        candidates.sort(key=lambda item: item.score, reverse=True)
        return candidates[:limit]


def reciprocal_rank_fusion(
    vector_results: list[RetrievalCandidate],
    keyword_results: list[RetrievalCandidate],
    top_k: int,
    k: int = 60,
) -> list[RetrievalCandidate]:
    by_chunk: dict[str, RetrievalCandidate] = {}
    fused_scores: defaultdict[str, float] = defaultdict(float)

    for rank, candidate in enumerate(vector_results, start=1):
        by_chunk[candidate.chunk.chunk_id] = candidate
        fused_scores[candidate.chunk.chunk_id] += 0.58 / (k + rank)

    for rank, candidate in enumerate(keyword_results, start=1):
        existing = by_chunk.get(candidate.chunk.chunk_id)
        if existing:
            existing.keyword_score = candidate.keyword_score
        else:
            by_chunk[candidate.chunk.chunk_id] = candidate
        fused_scores[candidate.chunk.chunk_id] += 0.42 / (k + rank)

    output = []
    for chunk_id, candidate in by_chunk.items():
        candidate.score = fused_scores[chunk_id] * 100
        output.append(candidate)
    output.sort(key=lambda item: item.score, reverse=True)
    return output[:top_k]


def _tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def _idf(corpus: list[list[str]]) -> dict[str, float]:
    doc_count = len(corpus)
    freq: defaultdict[str, int] = defaultdict(int)
    for tokens in corpus:
        for token in set(tokens):
            freq[token] += 1
    return {token: math.log((doc_count + 1) / (count + 0.5)) for token, count in freq.items()}


def _lexical_score(query_tokens: list[str], doc_tokens: list[str], idf: dict[str, float]) -> float:
    if not query_tokens or not doc_tokens:
        return 0.0
    doc_set = set(doc_tokens)
    return sum(idf.get(token, 0.0) for token in query_tokens if token in doc_set)


def _metadata_matches(chunk: DocumentChunk, filters: dict[str, str]) -> bool:
    metadata = chunk.metadata.model_dump()
    return all(_metadata_value_matches(metadata.get(key), value) for key, value in filters.items())


def _metadata_value_matches(actual, expected: str) -> bool:
    if isinstance(actual, list):
        return any(str(item).lower() == expected.lower() for item in actual)
    return str(actual or "").lower() == expected.lower()
