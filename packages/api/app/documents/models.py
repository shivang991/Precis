import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import String, DateTime, ForeignKey, func, Enum, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.shared.database import Base


class DocumentStatus(str, PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class DocumentSource(str, PyEnum):
    DIGITAL = "digital"   # Native PDF text extraction
    SCANNED = "scanned"   # OCR-based extraction


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    title: Mapped[str] = mapped_column(String(512))
    original_filename: Mapped[str] = mapped_column(String(512))

    # Storage key for the raw uploaded PDF in object storage
    storage_key: Mapped[str] = mapped_column(String(1024))

    source: Mapped[DocumentSource] = mapped_column(
        Enum(DocumentSource), default=DocumentSource.DIGITAL
    )
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus), default=DocumentStatus.PENDING, index=True
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Document-level settings (overrides user general settings)
    theme: Mapped[str | None] = mapped_column(String(64), nullable=True)
    include_headings_in_summary: Mapped[bool | None] = mapped_column(nullable=True)

    # The Standard Format document tree (see shared/standard_format.py)
    standard_format: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    page_count: Mapped[int | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped["User"] = relationship(back_populates="documents")  # noqa: F821
    highlights: Mapped[list["Highlight"]] = relationship(  # noqa: F821
        back_populates="document", cascade="all, delete-orphan"
    )
