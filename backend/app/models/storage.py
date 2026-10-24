import re
from datetime import datetime
from sqlalchemy import BigInteger, ForeignKey, String, TIMESTAMP, Index, func
from sqlalchemy.orm import Mapped, mapped_column
from pydantic import BaseModel, field_validator
from app.models.base import Base


class StorageFile(Base):
    __tablename__ = "storage_files"
    __table_args__ = (Index("idx_sf_hash", "sha256_hash"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(127), nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    uploaded_by_account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, nullable=False, server_default=func.now())


class StorageFileCreate(BaseModel):
    original_name: str
    file_path: str
    file_size_bytes: int
    mime_type: str
    sha256_hash: str
    uploaded_by_account_id: str

    @field_validator("sha256_hash")
    @classmethod
    def validate_sha256(cls, value: str) -> str:
        if not re.fullmatch(r"[0-9a-fA-F]{64}", value):
            raise ValueError("sha256_hash must be exactly 64 hexadecimal characters")
        return value
