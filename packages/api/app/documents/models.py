import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.database import Base


class DocumentStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class DocumentSource(StrEnum):
    DIGITAL = "digital"  # Native PDF text extraction
    SCANNED = "scanned"  # OCR-based extraction


class NodeType(StrEnum):
    heading = "heading"
    paragraph = "paragraph"
    list_item = "list_item"
    table = "table"
    image = "image"
    code = "code"


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
    nodes: Mapped[list["DocumentNode"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentNode.seq",
    )


class DocumentNode(Base):
    __tablename__ = "document_nodes"
    __table_args__ = (UniqueConstraint("document_id", "seq"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
    )
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_nodes.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    seq: Mapped[int] = mapped_column(Integer)

    type: Mapped[NodeType] = mapped_column(Enum(NodeType))
    level: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    page: Mapped[int | None] = mapped_column(Integer, nullable=True)

    document: Mapped["Document"] = relationship(back_populates="nodes")
