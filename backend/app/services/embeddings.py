"""
Embeddings Service — supports OpenAI AND Ollama (free local embeddings)
Falls back gracefully when OpenAI key is not set.
"""
from typing import List
import numpy as np
from app.config import settings

EMBEDDING_DIM = 1536


async def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed a list of texts. Uses Ollama if no OpenAI key, else OpenAI."""
    if not texts:
        return []
    if settings.openai_api_key and settings.openai_api_key.startswith("sk-"):
        return await _embed_openai(texts)
    return await _embed_ollama(texts)


async def embed_text(text: str) -> List[float]:
    results = await embed_texts([text])
    return results[0] if results else [0.0] * EMBEDDING_DIM


async def _embed_openai(texts: List[str]) -> List[List[float]]:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    response = await client.embeddings.create(model="text-embedding-3-small", input=texts)
    return [item.embedding for item in response.data]


async def _embed_ollama(texts: List[str]) -> List[List[float]]:
    """
    Use Ollama's local embedding model — nomic-embed-text (274MB, free).
    Pull it once: ollama pull nomic-embed-text
    Falls back to simple hash-based vectors if model not available.
    """
    import httpx
    base = settings.ollama_base_url.rstrip("/").replace("/v1", "")
    embeddings = []

    async with httpx.AsyncClient(timeout=60.0) as client:
        for text in texts:
            try:
                resp = await client.post(
                    f"{base}/api/embeddings",
                    json={"model": "nomic-embed-text", "prompt": text},
                )
                resp.raise_for_status()
                emb = resp.json().get("embedding", [])
                # Pad or truncate to EMBEDDING_DIM
                if len(emb) < EMBEDDING_DIM:
                    emb = emb + [0.0] * (EMBEDDING_DIM - len(emb))
                else:
                    emb = emb[:EMBEDDING_DIM]
                embeddings.append(emb)
            except Exception:
                # Fallback: deterministic pseudo-embedding from text hash
                # Not great for similarity but prevents hard crashes
                embeddings.append(_hash_embed(text))

    return embeddings


def _hash_embed(text: str) -> List[float]:
    """Deterministic fallback embedding using hash — not semantically meaningful."""
    import hashlib
    h = hashlib.sha256(text.encode()).digest()
    vec = []
    for i in range(EMBEDDING_DIM):
        byte = h[i % len(h)]
        vec.append((byte / 127.5) - 1.0)
    norm = np.linalg.norm(vec)
    return (np.array(vec) / norm).tolist() if norm > 0 else vec


def cosine_similarity(a: List[float], b: List[float]) -> float:
    a_arr, b_arr = np.array(a), np.array(b)
    na, nb = np.linalg.norm(a_arr), np.linalg.norm(b_arr)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(a_arr, b_arr) / (na * nb))


def average_pairwise_similarity(embeddings: List[List[float]]) -> float:
    if len(embeddings) < 2:
        return 1.0
    sims = [
        cosine_similarity(embeddings[i], embeddings[j])
        for i in range(len(embeddings))
        for j in range(i + 1, len(embeddings))
    ]
    return float(np.mean(sims))
