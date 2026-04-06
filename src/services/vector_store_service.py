"""
Vector Store Service — Manages Qdrant operations for menu item embeddings.

Each menu item is stored as a point with:
  - vector: 1536-dim from text-embedding-3-small
  - payload: menu_id, restaurant_name, item_name, item_price
"""

from __future__ import annotations

import logging
import uuid

from qdrant_client import QdrantClient, models

from src.helpers.config import get_settings

logger = logging.getLogger(__name__)

_client: QdrantClient | None = None


def _get_client() -> QdrantClient:
    """Lazy-init the Qdrant client."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = QdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)
    return _client


async def ensure_collection() -> None:
    """Create the menu_items collection if it does not exist."""
    settings = get_settings()
    client = _get_client()
    collection_name = settings.QDRANT_COLLECTION_NAME

    collections = client.get_collections().collections
    existing_names = [c.name for c in collections]

    if collection_name not in existing_names:
        client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=1536,  # text-embedding-3-small dimension
                distance=models.Distance.COSINE,
            ),
        )
        logger.info("Created Qdrant collection '%s'", collection_name)
    else:
        logger.info("Qdrant collection '%s' already exists", collection_name)


async def upsert_menu_items(
    menu_id: str,
    restaurant_name: str,
    items: list[dict],
    vectors: list[list[float]],
) -> int:
    """
    Upsert menu item embeddings into Qdrant.

    Args:
        menu_id: Unique menu identifier.
        restaurant_name: Name of the restaurant.
        items: List of dicts with 'name' and 'price'.
        vectors: Corresponding embedding vectors.

    Returns:
        Number of points upserted.
    """
    settings = get_settings()
    client = _get_client()

    points = []
    for item, vector in zip(items, vectors):
        point_id = str(uuid.uuid4())
        points.append(
            models.PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "menu_id": menu_id,
                    "restaurant_name": restaurant_name,
                    "item_name": item["name"],
                    "item_price": item["price"],
                },
            )
        )

    client.upsert(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        points=points,
    )

    logger.info(
        "Upserted %d points for menu '%s' (%s)",
        len(points),
        menu_id,
        restaurant_name,
    )
    return len(points)


async def search_similar(
    query_vector: list[float],
    menu_id: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """
    Search for similar menu items by vector.

    Args:
        query_vector: The query embedding vector.
        menu_id: Optional filter to search within a specific menu.
        limit: Max number of results.

    Returns:
        List of dicts with item_name, item_price, score, and restaurant_name.
    """
    settings = get_settings()
    client = _get_client()

    query_filter = None
    if menu_id:
        query_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="menu_id",
                    match=models.MatchValue(value=menu_id),
                )
            ]
        )

    results = client.query_points(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        query=query_vector,
        query_filter=query_filter,
        limit=limit,
    ).points

    items = []
    for hit in results:
        items.append(
            {
                "item_name": hit.payload.get("item_name", ""),
                "item_price": hit.payload.get("item_price", ""),
                "restaurant_name": hit.payload.get("restaurant_name", ""),
                "score": hit.score,
            }
        )

    logger.info("Search returned %d results", len(items))
    return items


async def get_items_by_menu_id(menu_id: str) -> list[dict]:
    """
    Retrieve all items for a given menu from Qdrant.

    Args:
        menu_id: The menu ID to filter by.

    Returns:
        List of dicts with item_name and item_price.
    """
    settings = get_settings()
    client = _get_client()

    results, _ = client.scroll(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        scroll_filter=models.Filter(
            must=[
                models.FieldCondition(
                    key="menu_id",
                    match=models.MatchValue(value=menu_id),
                )
            ]
        ),
        limit=1000,
    )

    items = []
    for point in results:
        items.append(
            {
                "item_name": point.payload.get("item_name", ""),
                "item_price": point.payload.get("item_price", ""),
            }
        )

    return items


async def delete_by_menu_id(menu_id: str) -> None:
    """Delete all vectors associated with a menu."""
    settings = get_settings()
    client = _get_client()

    client.delete(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="menu_id",
                        match=models.MatchValue(value=menu_id),
                    )
                ]
            )
        ),
    )

    logger.info("Deleted all vectors for menu '%s'", menu_id)
