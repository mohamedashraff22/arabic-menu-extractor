"""
Agent Runner — pure wiring, no business logic.

Creates and exposes three objects:
  - session_service: ADK DatabaseSessionService (PostgreSQL)
  - compaction_config: EventsCompactionConfig for context compression
  - runner: ADK Runner connecting the agent to the session service

All business logic (process_message, get_history, session resolution)
lives in chat_service.py.
"""

from __future__ import annotations

from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.adk.apps.app import EventsCompactionConfig

from src.agents import APP_NAME
from src.agents.menu_chat_agent import root_agent
from src.helpers.config import get_settings

settings = get_settings()

# ─── Session Service (PostgreSQL) ────────────────────────────────────
# Persists conversation history + state. ADK auto-creates tables.
session_service = DatabaseSessionService(db_url=settings.DATABASE_URL)

# ─── Compaction Config ───────────────────────────────────────────────
# Summarises old events to keep the LLM context window lean.
#   interval=5 → compact every 5 invocations
#   overlap=1  → include 1 prior event for continuity
compaction_config = EventsCompactionConfig(
    compaction_interval=5,
    overlap_size=1,
)

# ─── Runner ──────────────────────────────────────────────────────────
runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
)
