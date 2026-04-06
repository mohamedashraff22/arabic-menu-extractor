"""
Chat Controller — thin layer between routes and the chat service.

Delegates to agents/chat_service.py which owns session lifecycle
and agent invocation logic.
"""

from __future__ import annotations

import logging

from src.agents import chat_service

logger = logging.getLogger(__name__)


async def send_message(
    user_id: str,
    menu_id: str,
    message: str,
    session_id: str | None = None,
) -> dict:
    """
    Process a chat message through the ADK agent.

    Args:
        user_id: Unique user identifier.
        menu_id: The menu to chat about.
        message: User's message text.
        session_id: Optional existing session to resume.

    Returns:
        Dict with response text and session_id.
    """
    response_text, sid = await chat_service.process_message(
        user_id=user_id,
        menu_id=menu_id,
        user_text=message,
        session_id=session_id,
    )

    return {"response": response_text, "session_id": sid}


async def get_history(session_id: str) -> dict:
    """
    Retrieve chat history for a session.

    Args:
        session_id: The ADK session ID.

    Returns:
        Dict with session_id and list of messages.
    """
    messages = await chat_service.get_history(session_id)

    return {
        "session_id": session_id,
        "messages": messages,
    }
