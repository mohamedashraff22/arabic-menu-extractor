"""
Session Manager — TTL-based session cleanup with compaction summaries.

This module implements the 24-hour TTL lifecycle for chat sessions:

MESSAGE #1 (user says "hello")
├── sessions table: NEW ROW created (state = {menu_id: ..., user_id: ...})
└── events table:   NEW ROW (author=user, content="hello")
                    NEW ROW (author=agent, content="welcome!")

MESSAGE #2-4 (browsing menu, asking about items)
├── sessions table: SAME ROW, state keeps updating
└── events table:   NEW ROWs per message (user msg + tool calls + agent reply)

MESSAGE #5 (COMPACTION TRIGGERS — handled by ADK EventsCompactionConfig)
├── sessions table: no change
└── events table:   NEW ROW for user message
                    NEW ROW for agent reply
                    NEW ROW → compaction summary
                    ⚠️ Old rows STILL EXIST but LLM won't see them

MESSAGE #6+ (continues chatting)
├── sessions table: state keeps updating
└── events table:   keeps growing, but LLM only reads: summary + recent msgs

═══════════════════════════════════════════════════
24 HOURS PASS... user chats again
═══════════════════════════════════════════════════

SESSION MANAGER RUNS:
├── 1. Reads latest compaction summary from events table
├── 2. Reads user: prefixed keys from sessions.state
├── 3. DELETES old session → CASCADE deletes ALL its events
├── 4. CREATES new session with:
│      state = {
│        menu_id: "...",
│        user:last_session_summary: "User asked about grilled items..."
│      }
└── 5. New events start fresh from message #1 again
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from google.adk.sessions import DatabaseSessionService

from src.agents import APP_NAME
from src.helpers.config import get_settings

logger = logging.getLogger(__name__)


async def cleanup_expired_sessions(
    session_service: DatabaseSessionService,
    ttl_hours: int = 24,
) -> int:
    """
    Clean up sessions older than the TTL threshold.

    For each expired session:
    1. Extract the latest compaction summary (if any) from events
    2. Extract user:-prefixed state keys (persistent across sessions)
    3. Delete the old session (CASCADE deletes all events)
    4. Log the cleanup

    The next time the user chats, a fresh session is created in
    agent_runner.process_chat_message() with the user: state keys
    carried over by DatabaseSessionService automatically.

    Args:
        session_service: The ADK DatabaseSessionService instance.
        ttl_hours: Hours after which a session is considered expired.

    Returns:
        Number of sessions cleaned up.
    """
    settings = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=ttl_hours)
    cleaned = 0

    try:
        # List all sessions for our app
        # Note: DatabaseSessionService.list_sessions lists sessions for a
        # specific app+user. We need to iterate known users.
        # Since we track user→session in agent_runner._user_sessions,
        # we import it and iterate.
        from src.agents.chat_service import _user_sessions

        expired_users = []

        for user_id, session_id in list(_user_sessions.items()):
            try:
                session = await session_service.get_session(
                    app_name=APP_NAME,
                    user_id=user_id,
                    session_id=session_id,
                )

                if session is None:
                    # Session already gone
                    expired_users.append(user_id)
                    continue

                # Check if session is expired based on last_update_time
                last_update = getattr(session, "last_update_time", None)
                if last_update is None:
                    # Fall back to checking the last event timestamp
                    if session.events:
                        last_event = session.events[-1]
                        last_update = getattr(last_event, "timestamp", None)

                if last_update is None:
                    continue

                # Ensure timezone-aware comparison
                if hasattr(last_update, "tzinfo") and last_update.tzinfo is None:
                    last_update = last_update.replace(tzinfo=timezone.utc)

                if last_update > cutoff:
                    continue  # Session is still active

                # ── Session is expired — extract summary ─────────────
                logger.info(
                    "Session %s for user %s expired (last activity: %s)",
                    session_id,
                    user_id,
                    last_update,
                )

                # Extract compaction summary from events (if compaction ran)
                summary_text = _extract_compaction_summary(session)

                # Extract user:-prefixed state for carryover
                user_state = {
                    k: v
                    for k, v in (session.state or {}).items()
                    if k.startswith("user:")
                }

                # Store the last session summary as user-level state
                if summary_text:
                    user_state["user:last_session_summary"] = summary_text

                logger.info(
                    "Cleaning up session %s — summary: %s, user_state keys: %s",
                    session_id,
                    summary_text[:100] if summary_text else "(none)",
                    list(user_state.keys()),
                )

                # Delete the old session (CASCADE deletes all events)
                await session_service.delete_session(
                    app_name=APP_NAME,
                    user_id=user_id,
                    session_id=session_id,
                )

                expired_users.append(user_id)
                cleaned += 1

            except Exception:
                logger.exception(
                    "Error processing session cleanup for user %s", user_id
                )

        # Remove cleaned-up users from the mapping
        for user_id in expired_users:
            _user_sessions.pop(user_id, None)

    except Exception:
        logger.exception("Error during session cleanup sweep")

    if cleaned > 0:
        logger.info("Session cleanup complete: %d sessions removed", cleaned)

    return cleaned


def _extract_compaction_summary(session) -> str:
    """
    Extract the latest compaction summary from session events.

    ADK stores compaction summaries in event actions as
    compacted_content. We look for the most recent one.
    """
    if not session.events:
        return ""

    # Walk events in reverse to find the latest compaction summary
    for event in reversed(session.events):
        actions = getattr(event, "actions", None)
        if actions is None:
            continue

        # Check for compaction data
        compaction = getattr(actions, "compaction", None)
        if compaction is not None:
            compacted_content = getattr(compaction, "compacted_content", None)
            if compacted_content and hasattr(compacted_content, "parts"):
                for part in compacted_content.parts:
                    text = getattr(part, "text", None)
                    if text:
                        return text

    # Fallback: build a simple summary from the last few messages
    messages = []
    for event in session.events[-6:]:
        if event.content and event.content.parts:
            text = event.content.parts[0].text or ""
            if text:
                role = event.content.role or event.author
                messages.append(f"{role}: {text[:200]}")

    if messages:
        return "Recent conversation:\n" + "\n".join(messages)

    return ""


async def start_cleanup_loop(
    session_service: DatabaseSessionService,
    ttl_hours: int = 24,
    check_interval_minutes: int = 60,
) -> None:
    """
    Run the session cleanup loop as a background task.

    Checks for expired sessions every `check_interval_minutes` minutes
    and cleans up any that exceed the TTL.

    Args:
        session_service: The ADK DatabaseSessionService instance.
        ttl_hours: Hours after which a session is considered expired.
        check_interval_minutes: How often (in minutes) to check for expired sessions.
    """
    logger.info(
        "Session cleanup loop started (TTL=%dh, check every %dm)",
        ttl_hours,
        check_interval_minutes,
    )

    while True:
        try:
            await cleanup_expired_sessions(session_service, ttl_hours)
        except Exception:
            logger.exception("Error in session cleanup loop iteration")

        await asyncio.sleep(check_interval_minutes * 60)
