"""
Custom ADK tools for the Menu Chat Agent.

These tools let the agent search and retrieve menu items from Qdrant,
using the menu_id stored in the ADK session state.

Both tools are async — ADK natively supports async tool functions,
so there's no need for the run_until_complete workaround.
"""

from __future__ import annotations

import logging

from google.adk.tools import ToolContext

from src.services import embedding_service, vector_store_service

logger = logging.getLogger(__name__)


async def search_menu(query: str, tool_context: ToolContext) -> dict:
    """
    Search for menu items matching a description or keyword.

    Embeds the query and performs a cosine similarity search in Qdrant,
    filtered to the current menu (from session state).

    Args:
        query: A natural language description of what the user is looking for
               (e.g. "grilled chicken", "cheap drinks", "desserts").
        tool_context: ADK tool context providing access to session state.

    Returns:
        A dict with a list of matching items and their prices.
    """
    menu_id = tool_context.state.get("menu_id", "")
    if not menu_id:
        return {"error": "No menu selected. Please select a menu first."}

    try:
        query_vector = await embedding_service.embed_query(query)

        results = await vector_store_service.search_similar(
            query_vector=query_vector,
            menu_id=menu_id,
            limit=10,
        )

        if not results:
            return {"message": "No matching items found in this menu."}

        items = [
            {
                "name": r["item_name"],
                "price": r["item_price"],
                "relevance": round(r["score"], 3),
            }
            for r in results
        ]
        return {"items": items, "count": len(items)}

    except Exception as e:
        logger.exception("Error in search_menu tool")
        return {"error": f"Search failed: {str(e)}"}


async def get_menu_items(tool_context: ToolContext) -> dict:
    """
    Get all items from the current menu.

    Retrieves every item stored in Qdrant for the menu_id in session state.

    Args:
        tool_context: ADK tool context providing access to session state.

    Returns:
        A dict with all items from the menu.
    """
    menu_id = tool_context.state.get("menu_id", "")
    if not menu_id:
        return {"error": "No menu selected. Please select a menu first."}

    try:
        results = await vector_store_service.get_items_by_menu_id(menu_id)

        if not results:
            return {"message": "No items found for this menu."}

        items = [{"name": r["item_name"], "price": r["item_price"]} for r in results]
        return {"items": items, "count": len(items)}

    except Exception as e:
        logger.exception("Error in get_menu_items tool")
        return {"error": f"Failed to retrieve items: {str(e)}"}
