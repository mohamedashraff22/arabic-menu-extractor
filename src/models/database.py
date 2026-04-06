"""
SQLAlchemy async engine, session factory, and ORM models for menu metadata.

ADK's DatabaseSessionService manages its own tables (adk_sessions, etc.)
automatically. This module only defines the *application-specific* tables
for storing menu metadata.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from src.helpers.config import get_settings

# ── Engine & Session Factory ─────────────────────────────────────────
settings = get_settings()

engine = create_async_engine(settings.DATABASE_URL, echo=False)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# ── Base ─────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Menu Model ───────────────────────────────────────────────────────
class MenuRecord(Base):
    """Stores metadata about an uploaded restaurant menu."""

    __tablename__ = "menus"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    restaurant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    image_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    item_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationship to items
    items: Mapped[list["MenuItemRecord"]] = relationship(
        back_populates="menu",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Menu {self.id} '{self.restaurant_name}'>"


# ── Menu Item Model ──────────────────────────────────────────────────
class MenuItemRecord(Base):
    """Stores individual extracted items from a menu."""

    __tablename__ = "menu_items"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    menu_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("menus.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[str] = mapped_column(String(100), nullable=False)

    menu: Mapped["MenuRecord"] = relationship(back_populates="items")

    def __repr__(self) -> str:
        return f"<MenuItem '{self.name}' - {self.price}>"


# ── Table Creation Helper ────────────────────────────────────────────
async def create_tables() -> None:
    """Create all application tables (not ADK tables — those are auto-created)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
