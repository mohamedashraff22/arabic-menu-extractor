"""
Chat Service — business logic for processing chat messages and history.

Owns the user→session mapping, session lifecycle (create/resolve/validate),
and delegates the actual agent execution to the ADK Runner.

Separated from agent_runner.py (wiring) to follow single-responsibility.
"""

from __future__ import annotations

import logging

from google.genai import types

from src.agents import APP_NAME
from src.agents.agent_runner import runner, session_service

logger = logging.getLogger(__name__)

# Track user → session mappings (user_id → session_id).
# Also read by session_manager.py for TTL cleanup.
_user_sessions: dict[str, str] = {}


async def process_message(
    user_id: str,
    menu_id: str,
    user_text: str,
    session_id: str | None = None,
) -> tuple[str, str]:
    """
    Send a user message through the ADK agent and return (reply, session_id).

    Session lifecycle:
      1. If session_id provided → use it (resume)
      2. Else check cache → validate session still exists in DB
      3. If expired/missing → create a fresh session
      4. Run agent → return response

    Args:
        user_id:    Unique identifier for the user.
        menu_id:    The menu to chat about.
        user_text:  The user's message text.
        session_id: Optional existing session ID to resume.

    Returns:
        Tuple of (agent_response_text, session_id).
    """
    sid = await _resolve_session(user_id, menu_id, session_id)

    # Build user message in ADK format
    user_content = types.Content(
        role="user",
        parts=[types.Part.from_text(text=user_text)],
    )

    # Run the agent
    final_text = ""
    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=sid,
            new_message=user_content,
        ):
            if event.is_final_response():
                if event.content and event.content.parts:
                    final_text = event.content.parts[0].text or ""
    except Exception:
        logger.exception("Agent processing error for user %s", user_id)
        final_text = (
            "عذرًا، حدث خطأ أثناء المعالجة. حاول مرة أخرى.\n"
            "(Sorry, an error occurred. Please try again.)"
        )

    logger.info("Agent reply to %s: %s", user_id, final_text[:100])
    return final_text, sid


async def get_history(session_id: str) -> list[dict]:
    """
    Retrieve chat history for a given session.

    Args:
        session_id: The ADK session ID.

    Returns:
        List of dicts with role, content, and timestamp.
    """
    user_id = _find_user_for_session(session_id)
    if not user_id:
        return []

    try:
        session = await session_service.get_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )

        if not session or not session.events:
            return []

        messages = []
        for event in session.events:
            if event.content and event.content.parts:
                text = event.content.parts[0].text or ""
                if text:
                    messages.append(
                        {
                            "role": event.content.role or event.author,
                            "content": text,
                            "timestamp": getattr(event, "timestamp", None),
                        }
                    )
        return messages

    except Exception:
        logger.exception("Error retrieving session history for %s", session_id)
        return []


# ── Private helpers ──────────────────────────────────────────────────


async def _resolve_session(
    user_id: str,
    menu_id: str,
    session_id: str | None,
) -> str:
    """Resolve or create a valid session for this user."""

    # Explicit session_id takes priority
    if session_id:
        _user_sessions[user_id] = session_id

    # Validate cached session still exists (may have been TTL-cleaned)
    if user_id in _user_sessions:
        cached_sid = _user_sessions[user_id]
        try:
            existing = await session_service.get_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=cached_sid,
            )
            if existing is None:
                logger.info(
                    "Session %s for user %s was cleaned up, will create new",
                    cached_sid,
                    user_id,
                )
                del _user_sessions[user_id]
        except Exception:
            _user_sessions.pop(user_id, None)

    # Create new session if needed
    if user_id not in _user_sessions:
        session = await session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            state={"menu_id": menu_id},
        )
        _user_sessions[user_id] = session.id
        logger.info("Created new ADK session for %s: %s", user_id, session.id)

    return _user_sessions[user_id]


def _find_user_for_session(session_id: str) -> str | None:
    """Reverse-lookup: find the user_id that owns a session_id."""
    for uid, sid in _user_sessions.items():
        if sid == session_id:
            return uid
    return None
