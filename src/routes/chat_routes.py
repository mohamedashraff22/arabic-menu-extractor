"""
Chat Routes — FastAPI router for conversational menu Q&A via ADK agents.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.controllers import chat_controller
from src.models.schemas import (
    ChatRequest,
    ChatResponse,
    ChatHistoryResponse,
)

router = APIRouter(prefix="/api/v1/chat", tags=["Chat"])


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to the menu chat agent.

    The agent uses openai model and has tools to search and retrieve
    menu items from Qdrant. Session history is persisted in PostgreSQL
    via ADK's DatabaseSessionService.
    """
    try:
        result = await chat_controller.send_message(
            user_id=request.user_id,
            menu_id=request.menu_id,
            message=request.message,
            session_id=request.session_id,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


@router.get("/sessions/{session_id}/history", response_model=ChatHistoryResponse)
async def get_chat_history(session_id: str):
    """
    Retrieve chat history for a specific session.

    Returns all user and agent messages from the ADK session.
    """
    result = await chat_controller.get_history(session_id)
    if not result["messages"]:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found or has no messages",
        )
    return result
