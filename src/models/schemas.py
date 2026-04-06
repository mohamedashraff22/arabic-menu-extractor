"""
Pydantic schemas for API request / response validation.
"""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


# ── Menu Items ───────────────────────────────────────────────────────

class MenuItem(BaseModel):
    """A single extracted menu item."""
    name: str
    price: str


# ── Menu Upload ──────────────────────────────────────────────────────

class MenuUploadResponse(BaseModel):
    """Response returned after uploading and processing a menu image."""
    menu_id: str
    restaurant_name: str
    item_count: int
    status: str = "success"


# ── Menu Listing ─────────────────────────────────────────────────────

class MenuListItem(BaseModel):
    """Summary of a single menu for listing."""
    menu_id: str
    restaurant_name: str
    item_count: int
    created_at: datetime


class MenuListResponse(BaseModel):
    """Response containing all available menus."""
    menus: list[MenuListItem]
    total: int


# ── Menu Detail ──────────────────────────────────────────────────────

class MenuDetailResponse(BaseModel):
    """Full detail of a single menu including extracted items."""
    menu_id: str
    restaurant_name: str
    item_count: int
    created_at: datetime
    items: list[MenuItem]


# ── Menu Delete ──────────────────────────────────────────────────────

class MenuDeleteResponse(BaseModel):
    """Response after deleting a menu."""
    menu_id: str
    status: str = "deleted"


# ── Chat ─────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    """Request body for sending a chat message."""
    message: str = Field(..., min_length=1, description="User message text")
    menu_id: str = Field(..., description="ID of the menu to chat about")
    user_id: str = Field(..., description="Unique user identifier")
    session_id: str | None = Field(
        default=None,
        description="Existing session ID to continue conversation (optional)",
    )


class ChatResponse(BaseModel):
    """Response from the chat agent."""
    response: str
    session_id: str


class ChatMessage(BaseModel):
    """A single message in chat history."""
    role: str  # "user" or "agent"
    content: str
    timestamp: datetime | None = None


class ChatHistoryResponse(BaseModel):
    """Chat history for a session."""
    session_id: str
    messages: list[ChatMessage]
