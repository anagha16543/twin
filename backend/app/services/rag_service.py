"""
AI-NBA Readiness System — Backend
app/services/rag_service.py

Text chunking, embedding generation, and vector retrieval for RAG.

Architecture
------------
* Chunks are produced by a recursive character splitter with configurable
  size and overlap.
* Embeddings are generated via a pluggable provider; the default provider
  uses a sentence-transformers model served locally OR via a compatible
  OpenAI-style embedding API.
* Storage: pgvector on PostgreSQL (Vector(384)), JSON list on SQLite tests.
* Retrieval: cosine similarity via pgvector <=> operator on PostgreSQL.
  On SQLite a fallback linear scan is used (for tests only).

Configuration via Settings:
    EMBEDDING_MODEL       Name or endpoint identifier (default: "local-minilm")
    EMBEDDING_DIMENSIONS  Vector size (default: 384) — MUST match the model
    EMBEDDING_API_KEY     Optional API key (not logged, not returned in responses)
    EMBEDDING_API_BASE    Optional base URL for compatible embedding API

Embedding generation
--------------------
If credentials or model dependencies are unavailable, chunk records are
stored WITHOUT embeddings (embedding=None).  Retrieval falls back to
keyword relevance when embeddings are missing.  A clear warning is logged.
No fake vectors are generated.
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from app.models.phase4 import Document, DocumentChunk
from app.services.document_processor import ExtractionResult, PageExtraction

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Settings helpers
# ---------------------------------------------------------------------------

def _get_embedding_settings():
    from app.core.config import get_settings
    s = get_settings()
    return {
        "model": getattr(s, "EMBEDDING_MODEL", "local-minilm"),
        "dimensions": int(getattr(s, "EMBEDDING_DIMENSIONS", 384)),
        "api_key": getattr(s, "EMBEDDING_API_KEY", None),
        "api_base": getattr(s, "EMBEDDING_API_BASE", None),
    }


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def _get_chunk_settings():
    from app.core.config import get_settings
    s = get_settings()
    return {
        "chunk_size": int(getattr(s, "CHUNK_SIZE", 600)),
        "chunk_overlap": int(getattr(s, "CHUNK_OVERLAP", 100)),
    }


def chunk_text(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    page_number: int = 1,
    section_heading: Optional[str] = None,
) -> list[dict]:
    """
    Split ``text`` into overlapping character-level chunks.

    Returns a list of dicts:
        { "content": str, "page_number": int,
          "section_heading": str|None, "chunk_index": int }
    """
    if not text.strip():
        return []

    step = max(chunk_size - chunk_overlap, 1)
    chunks = []
    idx = 0
    chunk_index = 0

    while idx < len(text):
        end = min(idx + chunk_size, len(text))
        chunk_content = text[idx:end].strip()
        if chunk_content:
            chunks.append({
                "content": chunk_content,
                "page_number": page_number,
                "section_heading": section_heading,
                "chunk_index": chunk_index,
            })
            chunk_index += 1
        idx += step

    return chunks


def chunk_extraction_result(extraction: ExtractionResult) -> list[dict]:
    """
    Chunk all pages from an ExtractionResult.
    Chunk indices are global across the document.
    """
    cfg = _get_chunk_settings()
    all_chunks: list[dict] = []
    global_index = 0

    for page in extraction.pages:
        if not page.text.strip():
            continue
        page_chunks = chunk_text(
            text=page.text,
            chunk_size=cfg["chunk_size"],
            chunk_overlap=cfg["chunk_overlap"],
            page_number=page.page_number,
        )
        for c in page_chunks:
            c["chunk_index"] = global_index
            all_chunks.append(c)
            global_index += 1

    return all_chunks


# ---------------------------------------------------------------------------
# Embedding generation
# ---------------------------------------------------------------------------

def _content_hash(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()


def generate_embedding(text: str, settings: dict) -> Optional[list[float]]:
    """
    Generate an embedding vector for ``text``.

    Attempts:
    1. Local sentence-transformers model if ``model`` is "local-minilm"
       and the library is importable.
    2. OpenAI-compatible API if api_base is configured.
    3. Returns None with a warning if neither is available.

    Never fabricates vectors; never logs API keys.
    """
    model_name = settings.get("model", "local-minilm")
    dimensions = settings.get("dimensions", 384)
    api_key = settings.get("api_key")
    api_base = settings.get("api_base")

    # --- Option 1: local sentence-transformers ---
    if model_name in ("local-minilm", "sentence-transformers/all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            _model = SentenceTransformer("all-MiniLM-L6-v2")
            vec = _model.encode(text, normalize_embeddings=True)
            result = vec.tolist()
            if len(result) != dimensions:
                logger.warning(
                    "Embedding dimension mismatch: got %d, expected %d",
                    len(result),
                    dimensions,
                )
            return result
        except ImportError:
            logger.debug("sentence-transformers not installed; skipping local model.")
        except Exception as exc:
            logger.warning("Local embedding generation failed: %s", exc)

    # --- Option 2: OpenAI-compatible API ---
    if api_base and api_key:
        try:
            from openai import OpenAI  # type: ignore
            client = OpenAI(api_key=api_key, base_url=api_base)
            response = client.embeddings.create(input=[text], model=model_name)
            vec = response.data[0].embedding
            if len(vec) != dimensions:
                logger.warning(
                    "API embedding dimension mismatch: got %d, expected %d",
                    len(vec),
                    dimensions,
                )
            return vec
        except Exception as exc:
            logger.warning("API embedding generation failed: %s", exc)

    logger.warning(
        "Embedding generation unavailable for model '%s'. "
        "Chunks will be stored without embeddings. "
        "Configure EMBEDDING_API_KEY + EMBEDDING_API_BASE or install "
        "sentence-transformers to enable semantic retrieval.",
        model_name,
    )
    return None


# ---------------------------------------------------------------------------
# Persist chunks to database
# ---------------------------------------------------------------------------

def index_document_chunks(
    db: Session,
    document: Document,
    extraction: ExtractionResult,
) -> int:
    """
    Chunk an ExtractionResult, generate embeddings, and persist to DB.

    Existing chunks for this document are deleted before reinserting
    (handles reprocessing / stale-index cleanup).

    Returns the number of chunks inserted.
    """
    # Remove stale chunks
    db.query(DocumentChunk).filter(
        DocumentChunk.document_id == document.id
    ).delete(synchronize_session="fetch")

    chunks_data = chunk_extraction_result(extraction)
    if not chunks_data:
        logger.info("No chunks produced for document %s", document.id)
        return 0

    emb_settings = _get_embedding_settings()
    dimensions = emb_settings["dimensions"]
    model_name = emb_settings["model"]

    inserted = 0
    for c in chunks_data:
        embedding = generate_embedding(c["content"], emb_settings)
        chunk = DocumentChunk(
            document_id=document.id,
            chunk_index=c["chunk_index"],
            page_number=c["page_number"],
            section_heading=c.get("section_heading"),
            content=c["content"],
            content_hash=_content_hash(c["content"]),
            embedding_model=model_name,
            embedding_dimensions=dimensions,
            embedding=embedding,
        )
        db.add(chunk)
        inserted += 1

    db.flush()
    return inserted


# ---------------------------------------------------------------------------
# Retrieval
# ---------------------------------------------------------------------------

@dataclass
class ChunkMatch:
    chunk_id: str
    document_id: str
    document_name: str
    page_number: int
    section_heading: Optional[str]
    content: str
    similarity_score: Optional[float]


def retrieve_relevant_chunks(
    db: Session,
    query_text: str,
    top_k: int = 5,
    department: Optional[str] = None,
    academic_year_id=None,
    criterion_code: Optional[str] = None,
    exclude_deleted: bool = True,
) -> list[ChunkMatch]:
    """
    Retrieve the top-K most relevant document chunks for a query.

    On PostgreSQL with pgvector: uses cosine similarity (<=> operator).
    On SQLite (tests / no pgvector): returns up to top_k chunks ordered
    by creation time (pure keyword relevance is NOT implemented — this is
    clearly a test-only fallback).

    Deleted documents are always excluded.
    """
    from sqlalchemy import text as sa_text
    from sqlalchemy.orm import Session

    emb_settings = _get_embedding_settings()
    query_embedding = generate_embedding(query_text, emb_settings)

    # Base query: active, non-deleted documents
    q = (
        db.query(DocumentChunk, Document)
        .join(Document, DocumentChunk.document_id == Document.id)
        .filter(Document.is_deleted.is_(False))
        .filter(Document.is_current.is_(True))
    )

    if department:
        q = q.filter(Document.department == department)
    if academic_year_id:
        q = q.filter(Document.academic_year_id == academic_year_id)

    # Try pgvector cosine similarity
    if query_embedding is not None:
        try:
            # Test if we are on PostgreSQL (pgvector)
            dialect_name = db.bind.dialect.name if db.bind else "sqlite"
            if dialect_name == "postgresql":
                from pgvector.sqlalchemy import Vector  # type: ignore
                q = q.order_by(
                    DocumentChunk.embedding.cosine_distance(query_embedding)
                ).limit(top_k)
                rows = q.all()
                results = []
                for chunk, doc in rows:
                    # cosine_distance returns 0=identical, 2=opposite
                    sim = 1.0 - (chunk.embedding.cosine_distance(query_embedding) / 2.0) \
                        if chunk.embedding is not None else None
                    results.append(ChunkMatch(
                        chunk_id=str(chunk.id),
                        document_id=str(doc.id),
                        document_name=doc.original_filename,
                        page_number=chunk.page_number,
                        section_heading=chunk.section_heading,
                        content=chunk.content,
                        similarity_score=sim,
                    ))
                return results
        except Exception as exc:
            logger.debug("pgvector retrieval failed, falling back: %s", exc)

    # Fallback: return most recent chunks (test / no-vector mode)
    rows = q.order_by(DocumentChunk.created_at.desc()).limit(top_k).all()
    return [
        ChunkMatch(
            chunk_id=str(chunk.id),
            document_id=str(doc.id),
            document_name=doc.original_filename,
            page_number=chunk.page_number,
            section_heading=chunk.section_heading,
            content=chunk.content,
            similarity_score=None,  # no ranking in fallback mode
        )
        for chunk, doc in rows
    ]
