import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, func, Text, Integer
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String as SAString
from app.shared.database import Base


class Highlight(Base):
    """
    A highlight marks a range of text within a single node in a document's Standard Format.

    For character-level highlights:
      - node_id: the single content node selected
      - start_offset / end_offset: character offsets within that node's text
        (NULL = entire node is highlighted)
      - ancestor_node_ids: heading chain from root down to the highlighted node
        (auto-computed so the Summary View can reconstruct context)
    """
    __tablename__ = "highlights"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )

    # The StandardFormat node being highlighted
    node_id: Mapped[str] = mapped_column(SAString, nullable=False)

    # Character-level offsets within the node's text (NULL = whole node)
    start_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Full ancestor heading chain for the highlighted node:
    # [node_id, ...] — stored so summary doesn't need re-traversal
    ancestor_node_ids: Mapped[list[str]] = mapped_column(ARRAY(SAString), nullable=False)

    # Optional user annotation on the highlight
    note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # UI color tag (maps to theme color tokens)
    color: Mapped[str] = mapped_column(String(32), default="yellow")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    document: Mapped["Document"] = relationship(back_populates="highlights")  # noqa: F821
