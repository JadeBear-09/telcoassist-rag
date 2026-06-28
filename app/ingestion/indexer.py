from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from app.ingestion.embedder import cosine_similarity
from app.models import DocumentChunk, RequestIdentity, RetrievalCandidate
from app.security.acl import chunk_allowed_for_identity

CHUNKS_FILE = "chunks.jsonl"
EMBEDDINGS_FILE = "embeddings.jsonl"


class LocalChunkRepository:
    def __init__(self, processed_dir: Path) -> None:
        self.processed_dir = processed_dir
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        self.chunks_path = self.processed_dir / CHUNKS_FILE
        self.embeddings_path = self.processed_dir / EMBEDDINGS_FILE

    def write(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> None:
        with self.chunks_path.open("w", encoding="utf-8") as handle:
            for chunk in chunks:
                handle.write(chunk.model_dump_json() + "\n")

        with self.embeddings_path.open("w", encoding="utf-8") as handle:
            for chunk, embedding in zip(chunks, embeddings, strict=True):
                row = {"chunk_id": chunk.chunk_id, "embedding": embedding}
                handle.write(json.dumps(row) + "\n")

    def read_chunks(self) -> list[DocumentChunk]:
        if not self.chunks_path.exists():
            return []
        chunks: list[DocumentChunk] = []
        with self.chunks_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    chunks.append(DocumentChunk.model_validate_json(line))
        return chunks

    def read_embeddings(self) -> dict[str, list[float]]:
        if not self.embeddings_path.exists():
            return {}
        embeddings: dict[str, list[float]] = {}
        with self.embeddings_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                embeddings[row["chunk_id"]] = row["embedding"]
        return embeddings


class LocalVectorIndex:
    def __init__(self, chunks: list[DocumentChunk], embeddings: dict[str, list[float]]) -> None:
        self.chunks = chunks
        self.embeddings = embeddings

    def search(
        self,
        query_vector: list[float],
        limit: int,
        filters: dict[str, str] | None = None,
        identity: RequestIdentity | None = None,
    ) -> list[RetrievalCandidate]:
        matches: list[RetrievalCandidate] = []
        for chunk in self._filter_chunks(filters or {}, identity):
            vector = self.embeddings.get(chunk.chunk_id)
            if vector is None:
                continue
            score = cosine_similarity(query_vector, vector)
            matches.append(RetrievalCandidate(chunk=chunk, score=score, vector_score=score))
        matches.sort(key=lambda item: item.score, reverse=True)
        return matches[:limit]

    def _filter_chunks(
        self,
        filters: dict[str, str],
        identity: RequestIdentity | None,
    ) -> Iterable[DocumentChunk]:
        for chunk in self.chunks:
            metadata = chunk.metadata.model_dump()
            matches_filters = all(
                _metadata_value_matches(metadata.get(key), value)
                for key, value in filters.items()
            )
            if matches_filters:
                if not chunk_allowed_for_identity(chunk, identity):
                    continue
                yield chunk


class QdrantVectorIndex:
    def __init__(self, url: str, collection: str, vector_size: int) -> None:
        from qdrant_client import QdrantClient
        from qdrant_client.http import models

        self.models = models
        self.client = QdrantClient(url=url)
        self.collection = collection
        collections = self.client.get_collections().collections
        exists = any(item.name == collection for item in collections)
        if not exists:
            self.client.create_collection(
                collection_name=collection,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE,
                ),
            )

    def upsert(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> None:
        points = []
        for idx, (chunk, vector) in enumerate(zip(chunks, embeddings, strict=True)):
            payload = chunk.model_dump(mode="json")
            points.append(self.models.PointStruct(id=idx, vector=vector, payload=payload))
        if points:
            self.client.upsert(collection_name=self.collection, points=points)

    def search(
        self,
        query_vector: list[float],
        limit: int,
        filters: dict[str, str] | None = None,
        identity: RequestIdentity | None = None,
    ) -> list[RetrievalCandidate]:
        query_filter = self._build_filter(filters or {}, identity)
        results = self.client.search(
            collection_name=self.collection,
            query_vector=query_vector,
            query_filter=query_filter,
            limit=limit,
        )
        candidates: list[RetrievalCandidate] = []
        for result in results:
            chunk = DocumentChunk.model_validate(result.payload)
            if not chunk_allowed_for_identity(chunk, identity):
                continue
            candidates.append(
                RetrievalCandidate(
                    chunk=chunk,
                    score=float(result.score),
                    vector_score=float(result.score),
                )
            )
        return candidates

    def _build_filter(self, filters: dict[str, str], identity: RequestIdentity | None = None):
        conditions = []
        for key, value in filters.items():
            conditions.append(
                self.models.FieldCondition(
                    key=f"metadata.{key}",
                    match=self.models.MatchValue(value=value),
                )
            )

        acl_filter = self._build_acl_filter(identity)
        if acl_filter is not None:
            conditions.append(acl_filter)

        if not conditions:
            return None
        return self.models.Filter(must=conditions)

    def _build_acl_filter(self, identity: RequestIdentity | None):
        public_acl = self.models.Filter(
            must=[
                self._empty_or_null("metadata.tenant_id"),
                self._empty("metadata.allowed_roles"),
                self._empty("metadata.allowed_users"),
            ]
        )

        if identity is None:
            return public_acl

        tenant_match = (
            self.models.FieldCondition(
                key="metadata.tenant_id",
                match=self.models.MatchValue(value=identity.tenant_id),
            )
            if identity.tenant_id
            else None
        )
        tenant_or_public = (
            self.models.Filter(should=[tenant_match, self._empty_or_null("metadata.tenant_id")])
            if tenant_match is not None
            else self._empty_or_null("metadata.tenant_id")
        )

        allowed = [public_acl]
        if tenant_match is not None:
            allowed.append(
                self.models.Filter(
                    must=[
                        tenant_match,
                        self._empty("metadata.allowed_roles"),
                        self._empty("metadata.allowed_users"),
                    ]
                )
            )
        if identity.user_id:
            allowed.append(
                self.models.Filter(
                    must=[
                        tenant_or_public,
                        self.models.FieldCondition(
                            key="metadata.allowed_users",
                            match=self.models.MatchValue(value=identity.user_id),
                        ),
                    ]
                )
            )
        if identity.roles:
            allowed.append(
                self.models.Filter(
                    must=[
                        tenant_or_public,
                        self.models.FieldCondition(
                            key="metadata.allowed_roles",
                            match=self.models.MatchAny(any=identity.roles),
                        ),
                    ]
                )
            )
        return self.models.Filter(should=allowed)

    def _empty(self, key: str):
        return self.models.IsEmptyCondition(is_empty=self.models.PayloadField(key=key))

    def _empty_or_null(self, key: str):
        return self.models.Filter(
            should=[
                self._empty(key),
                self.models.IsNullCondition(is_null=self.models.PayloadField(key=key)),
            ]
        )


def _metadata_value_matches(actual, expected: str) -> bool:
    if isinstance(actual, list):
        return any(str(item).lower() == expected.lower() for item in actual)
    return str(actual or "").lower() == expected.lower()
