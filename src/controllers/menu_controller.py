"""
Menu Controller — Orchestrates the full menu upload and management pipeline.

Flow: Image upload → OCR extraction → Embedding → Qdrant storage → DB metadata
"""

from __future__ import annotations

import logging
import uuid
import os
from datetime import datetime, timezone

from sqlalchemy import select, delete as sa_delete

from src.models.database import (
    async_session_factory,
    MenuRecord,
    MenuItemRecord,
)
from src.services import ocr_service, embedding_service, vector_store_service

logger = logging.getLogger(__name__)


async def upload_menu(
    image_bytes: bytes,
    image_filename: str,
    restaurant_name: str,
) -> dict:
    """
    Process a menu image end-to-end:
    1. OCR extraction via Kaggle
    2. Embed each item
    3. Store vectors in Qdrant
    4. Save metadata in PostgreSQL

    Returns:
        Dict with menu_id, restaurant_name, item_count, status.
    """
    menu_id = str(uuid.uuid4())

    # 1. Extract menu items via OCR
    logger.info("Starting OCR extraction for '%s'", restaurant_name)
    items = await ocr_service.extract_menu_from_image(image_bytes)

    if not items:
        raise ValueError("OCR returned no menu items. The image may be unclear.")

    # Save the original image locally so the frontend can retrieve it
    upload_dir = os.path.join(os.getcwd(), ".uploads")
    os.makedirs(upload_dir, exist_ok=True)
    image_path = os.path.join(upload_dir, f"{menu_id}.jpg")
    with open(image_path, "wb") as f:
        f.write(image_bytes)

    # 2. Embed each item individually
    texts = [
        embedding_service.format_menu_item_text(item["name"], item["price"])
        for item in items
    ]
    vectors = await embedding_service.embed_texts(texts)

    # 3. Store vectors in Qdrant
    await vector_store_service.upsert_menu_items(
        menu_id=menu_id,
        restaurant_name=restaurant_name,
        items=items,
        vectors=vectors,
    )

    # 4. Save metadata in PostgreSQL
    async with async_session_factory() as session:
        menu_record = MenuRecord(
            id=menu_id,
            restaurant_name=restaurant_name,
            image_filename=image_filename,
            item_count=len(items),
        )

        for item in items:
            menu_item = MenuItemRecord(
                menu_id=menu_id,
                name=item["name"],
                price=item["price"],
            )
            menu_record.items.append(menu_item)

        session.add(menu_record)
        await session.commit()

    logger.info(
        "Menu '%s' (%s) uploaded: %d items",
        menu_id,
        restaurant_name,
        len(items),
    )

    return {
        "menu_id": menu_id,
        "restaurant_name": restaurant_name,
        "item_count": len(items),
        "status": "success",
    }


async def list_menus() -> dict:
    """
    List all uploaded menus.

    Returns:
        Dict with list of menu summaries and total count.
    """
    async with async_session_factory() as session:
        result = await session.execute(
            select(MenuRecord).order_by(MenuRecord.created_at.desc())
        )
        menus = result.scalars().all()

    menu_list = [
        {
            "menu_id": m.id,
            "restaurant_name": m.restaurant_name,
            "item_count": m.item_count,
            "created_at": m.created_at,
        }
        for m in menus
    ]

    return {"menus": menu_list, "total": len(menu_list)}


async def get_menu_detail(menu_id: str) -> dict | None:
    """
    Get full details of a specific menu including all items.

    Returns:
        Dict with menu details and items, or None if not found.
    """
    async with async_session_factory() as session:
        result = await session.execute(
            select(MenuRecord).where(MenuRecord.id == menu_id)
        )
        menu = result.scalar_one_or_none()

    if menu is None:
        return None

    return {
        "menu_id": menu.id,
        "restaurant_name": menu.restaurant_name,
        "item_count": menu.item_count,
        "created_at": menu.created_at,
        "items": [{"name": item.name, "price": item.price} for item in menu.items],
    }


async def delete_menu(menu_id: str) -> bool:
    """
    Delete a menu: remove from PostgreSQL and Qdrant.

    Returns:
        True if found and deleted, False if not found.
    """
    async with async_session_factory() as session:
        result = await session.execute(
            select(MenuRecord).where(MenuRecord.id == menu_id)
        )
        menu = result.scalar_one_or_none()

        if menu is None:
            return False

        await session.execute(
            sa_delete(MenuRecord).where(MenuRecord.id == menu_id)
        )
        await session.commit()

    # Also remove vectors from Qdrant
    await vector_store_service.delete_by_menu_id(menu_id)

    # Delete the stored image
    import os
    image_path = os.path.join(os.getcwd(), ".uploads", f"{menu_id}.jpg")
    if os.path.exists(image_path):
        os.remove(image_path)

    logger.info("Deleted menu '%s'", menu_id)
    return True
