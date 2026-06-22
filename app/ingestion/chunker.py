from __future__ import annotations

import hashlib
import re

from app.models import DocumentChunk, DocumentMetadata


def chunk_document(
    text: str,
    metadata: DocumentMetadata,
    max_chars: int = 1200,
    overlap_chars: int = 160,
) -> list[DocumentChunk]:
    if not text.strip():
        return []

    sections = _split_sections(text)
    chunks: list[str] = []
    current = ""

    for section in sections:
        if len(section) > max_chars:
            if current:
                chunks.extend(_window_text(current, max_chars, overlap_chars))
                current = ""
            chunks.extend(_window_text(section, max_chars, overlap_chars))
            continue

        candidate = f"{current}\n\n{section}".strip() if current else section
        if len(candidate) <= max_chars:
            current = candidate
        else:
            chunks.append(current)
            current = section

    if current:
        chunks.append(current)

    output: list[DocumentChunk] = []
    for index, chunk_text in enumerate(chunks):
        normalized = chunk_text.strip()
        chunk_id = _chunk_id(metadata.doc_id, index, normalized)
        output.append(
            DocumentChunk(
                chunk_id=chunk_id,
                doc_id=metadata.doc_id,
                text=normalized,
                chunk_index=index,
                metadata=metadata,
                token_estimate=max(1, len(normalized.split())),
            )
        )
    return output


def _split_sections(text: str) -> list[str]:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    sections: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) <= 1600:
            sections.append(paragraph)
            continue
        sentences = re.split(r"(?<=[.!?])\s+", paragraph)
        sections.extend(sentence.strip() for sentence in sentences if sentence.strip())
    return sections


def _window_text(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    windows: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        window = text[start:end].strip()
        if window:
            windows.append(window)
        if end == len(text):
            break
        start = max(0, end - overlap_chars)
    return windows


def _chunk_id(doc_id: str, index: int, text: str) -> str:
    digest = hashlib.sha1(f"{doc_id}:{index}:{text}".encode("utf-8")).hexdigest()[:16]
    return f"{doc_id}_CH_{index:04d}_{digest}"
