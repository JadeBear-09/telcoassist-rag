from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass


TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]+")


@dataclass
class Embedder:
    provider: str = "hashing"
    model_name: str = "BAAI/bge-small-en-v1.5"
    dim: int = 384

    def __post_init__(self) -> None:
        self._model = None
        if self.provider == "sentence-transformers":
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(self.model_name)
            except Exception:
                self.provider = "hashing"
                self._model = None

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self._model is not None:
            vectors = self._model.encode(texts, normalize_embeddings=True)
            return [vector.tolist() for vector in vectors]
        return [hashing_embedding(text, self.dim) for text in texts]

    def embed_query(self, query: str) -> list[float]:
        return self.embed_texts([query])[0]


def hashing_embedding(text: str, dim: int = 384) -> list[float]:
    vector = [0.0] * dim
    tokens = TOKEN_RE.findall(text.lower())
    if not tokens:
        return vector

    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        bucket = int.from_bytes(digest[:4], "big") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[bucket] += sign

    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right))
