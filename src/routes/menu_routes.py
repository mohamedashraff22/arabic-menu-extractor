"""
Menu Routes — FastAPI router for menu upload, listing, detail, and deletion.
"""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from fastapi.responses import FileResponse

from src.controllers import menu_controller
from src.models.schemas import (
    MenuUploadResponse,
    MenuListResponse,
    MenuDetailResponse,
    MenuDeleteResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/menus", tags=["Menus"])


@router.post("/upload", response_model=MenuUploadResponse)
async def upload_menu(
    file: UploadFile = File(..., description="Menu image file (jpg, jpeg, png, etc.)"),
    restaurant_name: str = Form(..., description="Name of the restaurant"),
):
    """
    Upload a menu image and extract items.

    1. Sends image to Kaggle OCR endpoint for extraction
    2. Embeds each extracted item with OpenAI text-embedding-3-small
    3. Stores vectors in Qdrant with metadata
    4. Saves menu metadata in PostgreSQL
    """
    # Validate file type
    if file.content_type and not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail=f"File must be an image, got: {file.content_type}",
        )

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Empty file uploaded")

    try:
        result = await menu_controller.upload_menu(
            image_bytes=image_bytes,
            image_filename=file.filename or "unknown.jpg",
            restaurant_name=restaurant_name,
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.exception("Upload failed for '%s'", restaurant_name)
        error_detail = f"{type(e).__name__}: {e}" or "Unknown error"
        raise HTTPException(status_code=500, detail=f"Upload failed: {error_detail}")


@router.get("", response_model=MenuListResponse)
async def list_menus():
    """List all available menus with summary info."""
    result = await menu_controller.list_menus()
    return result


@router.get("/{menu_id}", response_model=MenuDetailResponse)
async def get_menu(menu_id: str):
    """Get full details of a specific menu including all extracted items."""
    result = await menu_controller.get_menu_detail(menu_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Menu '{menu_id}' not found")
    return result


@router.delete("/{menu_id}", response_model=MenuDeleteResponse)
async def delete_menu(menu_id: str):
    """Delete a menu and all its associated vectors from Qdrant."""
    deleted = await menu_controller.delete_menu(menu_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Menu '{menu_id}' not found")
    return {"menu_id": menu_id, "status": "deleted"}


@router.get("/{menu_id}/image")
async def get_menu_image(menu_id: str):
    """Serve the original uploaded menu image."""
    image_path = os.path.join(os.getcwd(), ".uploads", f"{menu_id}.jpg")
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(image_path)

