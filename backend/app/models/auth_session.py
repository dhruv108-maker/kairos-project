"""Revocable, per-login refresh sessions with a fixed seven-day absolute lifetime."""
from datetime import datetime
from sqlalchemy import ForeignKey, Index, String, TIMESTAMP, func
from sqlalchemy.dialects.mysql import BIGINT as MYSQL_BIGINT
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (
        Index("ix_auth_sessions_account_expires", "account_id", "expires_at"),
        Index("ix_auth_sessions_expires", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    account_id: Mapped[int | str] = mapped_column(
        MYSQL_BIGINT(unsigned=True).with_variant(String(36), "sqlite"),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    refresh_token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
    last_used_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    token_version: Mapped[int] = mapped_column(nullable=False)
