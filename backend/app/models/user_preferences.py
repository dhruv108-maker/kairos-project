from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.mysql import BIGINT as MYSQL_BIGINT
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserPreferences(Base):
    """Per-account preferences; never shared at institution or platform scope."""

    __tablename__ = "user_preferences"

    # The deployed accounts table uses unsigned BIGINT IDs. Keep string IDs only
    # for SQLite's isolated tests, whose account fixtures intentionally use UUID-like keys.
    account_id: Mapped[int | str] = mapped_column(
        MYSQL_BIGINT(unsigned=True).with_variant(String(36), "sqlite"),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    accent_color: Mapped[str] = mapped_column(String(16), nullable=False, server_default="teal")
    font_size: Mapped[str] = mapped_column(String(16), nullable=False, server_default="default")
    interface_density: Mapped[str] = mapped_column(String(16), nullable=False, server_default="comfortable")
    theme_mode: Mapped[str] = mapped_column(String(16), nullable=False, server_default="system")
    email_notifications_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    notification_preferences: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
