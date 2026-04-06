"""
FastAPI application entry point for the Arabic Menu Extractor.

Registers all routers and handles startup initialization:
  - PostgreSQL tables for menu metadata
  - Qdrant collection for vector embeddings
  - Background session TTL cleanup loop
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.helpers.config import get_settings

# LiteLLM reads OPENAI_API_KEY from os.environ — export it early
_settings = get_settings()
os.environ.setdefault("OPENAI_API_KEY", _settings.OPENAI_API_KEY)

from src.models.database import create_tables
from src.services.vector_store_service import ensure_collection
from src.agents.agent_runner import session_service
from src.agents.session_manager import start_cleanup_loop
from src.routes.menu_routes import router as menu_router
from src.routes.chat_routes import router as chat_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# Keep a reference to the background task so it doesn't get GC'd
_cleanup_task: asyncio.Task | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    global _cleanup_task
    settings = get_settings()

    # ── Startup ──────────────────────────────────────────────────
    logger.info("Initializing application...")

    # Create PostgreSQL tables for menu metadata
    await create_tables()
    logger.info("PostgreSQL tables ready")

    # Create Qdrant collection if needed
    await ensure_collection()
    logger.info("Qdrant collection ready")

    # Start background session TTL cleanup loop
    _cleanup_task = asyncio.create_task(
        start_cleanup_loop(
            session_service=session_service,
            ttl_hours=settings.SESSION_TTL_HOURS,
            check_interval_minutes=settings.SESSION_CLEANUP_INTERVAL_MINUTES,
        )
    )
    logger.info(
        "Session cleanup loop started (TTL=%dh, interval=%dm)",
        settings.SESSION_TTL_HOURS,
        settings.SESSION_CLEANUP_INTERVAL_MINUTES,
    )

    logger.info("Application started successfully")
    yield

    # ── Shutdown ─────────────────────────────────────────────────
    if _cleanup_task and not _cleanup_task.done():
        _cleanup_task.cancel()
        try:
            await _cleanup_task
        except asyncio.CancelledError:
            pass
    logger.info("Application shutting down")


# ── App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title="Arabic Menu Extractor API",
    description=(
        "End-to-end RAG application for Arabic restaurant menus. "
        "Upload menu images → OCR extraction → vector embeddings → "
        "conversational chat via ADK agents with context compaction "
        "and 24-hour session TTL cleanup."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ───────────────────────────────────────────────────────────
app.include_router(menu_router)
app.include_router(chat_router)


@app.get("/api/v1/health", tags=["Health"])
async def health_check():
    """Health check endpoint — verifies the API is running."""
    settings = get_settings()
    return {
        "status": "healthy",
        "service": "arabic-menu-extractor",
        "version": "0.1.0",
        "session_ttl_hours": settings.SESSION_TTL_HOURS,
    }
