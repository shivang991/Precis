import uuid
from datetime import datetime
from enum import StrEnum
from typing import ClassVar, Literal

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
    text = "text"
    table = "table"
    image = "image"


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )

    title: Mapped[str] = mapped_column(String(512))
    original_filename: Mapped[str] = mapped_column(String(512))

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
    text_highlights: Mapped[list["TextHighlight"]] = relationship(  # noqa: F821
        back_populates="document", cascade="all, delete-orphan"
    )
    table_highlights: Mapped[list["TableHighlight"]] = relationship(  # noqa: F821
        back_populates="document", cascade="all, delete-orphan"
    )
    image_highlights: Mapped[list["ImageHighlight"]] = relationship(  # noqa: F821
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

    document: Mapped["Document"] = relationship(back_populates="nodes")

    text_content: Mapped["TextContent | None"] = relationship(
        back_populates="node",
        uselist=False,
        cascade="all, delete-orphan",
        single_parent=True,
    )
    table_content: Mapped["TableContent | None"] = relationship(
        back_populates="node",
        uselist=False,
        cascade="all, delete-orphan",
        single_parent=True,
    )
    image_content: Mapped["ImageContent | None"] = relationship(
        back_populates="node",
        uselist=False,
        cascade="all, delete-orphan",
        single_parent=True,
    )

    @property
    def content(self) -> "TextContent | TableContent | ImageContent | None":
        return {
            NodeType.text: self.text_content,
            NodeType.table: self.table_content,
            NodeType.image: self.image_content,
        }[self.type]


class TextContent(Base):
    __tablename__ = "text_contents"

    type: ClassVar[Literal[NodeType.text]] = NodeType.text

    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_nodes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    text: Mapped[str] = mapped_column(Text)
    level: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)

    node: Mapped["DocumentNode"] = relationship(back_populates="text_content")


class TableContent(Base):
    __tablename__ = "table_contents"

    type: ClassVar[Literal[NodeType.table]] = NodeType.table

    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_nodes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    rows: Mapped[list] = mapped_column(JSONB)
    headers: Mapped[list | None] = mapped_column(JSONB, nullable=True)

    node: Mapped["DocumentNode"] = relationship(back_populates="table_content")


class ImageContent(Base):
    __tablename__ = "image_contents"

    type: ClassVar[Literal[NodeType.image]] = NodeType.image

    node_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_nodes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    storage_key: Mapped[str] = mapped_column(String(1024))
    alt: Mapped[str | None] = mapped_column(Text, nullable=True)

    node: Mapped["DocumentNode"] = relationship(back_populates="image_content")
