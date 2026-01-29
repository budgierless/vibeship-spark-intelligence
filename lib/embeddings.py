"""Optional embeddings helper (fastembed)."""

from __future__ import annotations

import os
from typing import List, Optional

_EMBEDDER = None
_EMBEDDER_ERROR = None


def _get_embedder():
    global _EMBEDDER, _EMBEDDER_ERROR
    if os.environ.get("SPARK_EMBEDDINGS", "1").lower() in ("0", "false", "no"):
        return None
    if _EMBEDDER is not None:
        return _EMBEDDER
    if _EMBEDDER_ERROR is not None:
        return None
    try:
        from fastembed import TextEmbedding
    except Exception as e:
        _EMBEDDER_ERROR = e
        return None
    model = os.environ.get("SPARK_EMBED_MODEL", "BAAI/bge-small-en-v1.5")
    try:
        _EMBEDDER = TextEmbedding(model_name=model)
    except Exception as e:
        _EMBEDDER_ERROR = e
        return None
    return _EMBEDDER


def embed_texts(texts: List[str]) -> Optional[List[List[float]]]:
    embedder = _get_embedder()
    if embedder is None:
        return None
    try:
        vectors = list(embedder.embed(texts))
        return [list(v) for v in vectors]
    except Exception:
        return None


def embed_text(text: str) -> Optional[List[float]]:
    if not text:
        return None
    vectors = embed_texts([text])
    if not vectors:
        return None
    return vectors[0]
