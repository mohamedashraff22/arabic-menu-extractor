"""
Embedding Service — Wraps OpenAI's text-embedding-3-small model.

Each menu item is embedded individually as "{name} - {price}" for
maximum precision in item-level search.
"""

from __future__ import annotations

import logging

from openai import AsyncOpenAI

from src.helpers.config import get_settings

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    """Lazy-init the async OpenAI client."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embed a batch of text strings using OpenAI text-embedding-3-small.

    Args:
        texts: List of strings to embed.

    Returns:
        List of embedding vectors (each 1536-dimensional).
    """
    settings = get_settings()
    client = _get_client()

    logger.info(
        "Embedding %d texts with %s", len(texts), settings.OPENAI_EMBEDDING_MODEL
    )

    response = await client.embeddings.create(
        input=texts,
        model=settings.OPENAI_EMBEDDING_MODEL,
    )

    vectors = [item.embedding for item in response.data]
    logger.info("Received %d vectors of dim %d", len(vectors), len(vectors[0]))
    return vectors


async def embed_query(query: str) -> list[float]:
    """
    Embed a single query string.

    Args:
        query: The search query to embed.

    Returns:
        A single 1536-dimensional embedding vector.
    """
    vectors = await embed_texts([query])
    return vectors[0]


def format_menu_item_text(name: str, price: str) -> str:
    """Format a menu item for embedding: '{name} - {price}'."""
    return f"{name} - {price}"
