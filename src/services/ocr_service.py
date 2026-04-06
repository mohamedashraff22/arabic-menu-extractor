"""
OCR Service — Proxies menu images to the Kaggle-hosted Qwen2.5-VL model
via an ngrok tunnel.

The Kaggle notebook exposes POST /generate which accepts a base64 image,
runs it through the fine-tuned VLM, and returns extracted menu items as JSON.
"""

from __future__ import annotations

import base64
import logging

import httpx
import json_repair

from src.helpers.config import get_settings

logger = logging.getLogger(__name__)


async def extract_menu_from_image(image_bytes: bytes) -> list[dict]:
    """
    Send a menu image to the Kaggle OCR endpoint and return parsed items.

    Args:
        image_bytes: Raw bytes of the uploaded image file.

    Returns:
        A list of dicts, each with 'name' and 'price' keys.

    Raises:
        httpx.HTTPStatusError: If the Kaggle endpoint returns non-200.
        ValueError: If the response cannot be parsed into menu items.
    """
    settings = get_settings()

    # 1. Encode image to base64
    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    # 2. POST to the Kaggle ngrok endpoint
    payload = {"image_base64": base64_image}

    # Use timeout=None so it doesn't drop the connection while Kaggle processes the image
    async with httpx.AsyncClient(timeout=None) as client:
        logger.info("Sending image to Kaggle OCR at %s", settings.KAGGLE_OCR_URL)
        response = await client.post(settings.KAGGLE_OCR_URL, json=payload)
        response.raise_for_status()

    # 3. Parse the response
    data = response.json()
    raw_output = data.get("data", "")

    try:
        parsed = json_repair.loads(raw_output)
    except Exception:
        logger.warning("json_repair failed, wrapping raw output")
        parsed = {"raw_text": raw_output}

    # 4. Extract the items list
    items: list[dict] = []

    logger.info("Raw OCR parsed output (%s): %s", type(parsed).__name__, str(parsed)[:2000])

    if isinstance(parsed, dict) and "items" in parsed:
        items = parsed["items"]
    elif isinstance(parsed, list):
        items = parsed
    else:
        logger.warning("Unexpected OCR output format: %s", type(parsed))
        raise ValueError(f"Could not parse menu items from OCR output: {parsed}")

    logger.info("Total items found before validation: %d", len(items))

    # 5. Validate each item has 'name' and 'price'
    validated: list[dict] = []
    for i, item in enumerate(items):
        if isinstance(item, dict) and "name" in item and "price" in item:
            validated.append({"name": str(item["name"]), "price": str(item["price"])})
        else:
            logger.warning("Dropped item #%d (missing name/price): %s", i, item)

    logger.info("Extracted %d menu items from OCR (%d dropped)", len(validated), len(items) - len(validated))
    return validated

