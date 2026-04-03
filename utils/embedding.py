"""
Shared embedding utilities for vector search.

Provides Ollama bge-m3 embedding generation, binary serialization,
cosine similarity, and RRF (Reciprocal Rank Fusion) merge.

Used by: memory_server.py, vault_index_server.py
"""
import json
import logging
import math
import os
import struct
import urllib.request
from typing import Optional

logger = logging.getLogger(__name__)

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11435")


def get_embedding(text: str, model: str = None) -> Optional[list]:
    """Generate text embedding via Ollama API.

    Args:
        text: Input text to embed.
        model: Ollama model name. Defaults to MEMORY_EMBED_MODEL or bge-m3.
    """
    if model is None:
        model = os.environ.get("MEMORY_EMBED_MODEL",
                               os.environ.get("VAULT_EMBED_MODEL", "bge-m3"))
    try:
        req = urllib.request.Request(
            f"{OLLAMA_URL}/api/embed",
            data=json.dumps({"model": model, "input": text}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read())
            if "embeddings" in result and len(result["embeddings"]) > 0:
                return result["embeddings"][0]
    except Exception as e:
        logger.error(f"Embedding error: {e}")
    return None


def embedding_to_blob(emb: list) -> bytes:
    """Serialize float list to binary blob for SQLite storage."""
    return struct.pack(f"{len(emb)}f", *emb)


def blob_to_embedding(blob: bytes) -> list:
    """Deserialize binary blob back to float list."""
    n = len(blob) // 4
    return list(struct.unpack(f"{n}f", blob))


def cosine_similarity(a: list, b: list) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)
