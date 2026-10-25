from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class UserPreferences(Base):
    """Per-account preferences; never shared at institution or platform scope."""

    __tablename__ = "user_preferences"

    # Match accounts.id exactly: BIGINT UNSIGNED AUTO_INCREMENT.
    account_id: Mapped[int] = mapped_column(
        BIGINT(unsigned=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    accent_color: Mapped[str] = mapped_column(String(16), nullable=False, server_default="teal")
    font_size: Mapped[str] = mapped_column(String(16), nullable=False, server_default="default")
    interface_density: Mapped[str] = mapped_column(__import__("sqlalchemy").String(16), nullable=False, server_default="comfortable")
    theme_mode: Mapped[str] = mapped_column(__import__("sqlalchemy").String(16), nullable=False, server_default="system")
    email_notifications_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="1")
    notification_preferences: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
