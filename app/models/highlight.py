import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, func, Text
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String as SAString
from app.database import Base


class Highlight(Base):
    """
    A highlight marks one or more node IDs within a document's Standard Format.

    When a user highlights a passage, we record:
      - node_ids: the IDs of the content nodes selected
      - ancestor_node_ids: heading chain from root down to the highlighted node
        (auto-computed so the Summary View can reconstruct context)
    """
    __tablename__ = "highlights"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), index=True
    )

    # IDs of the highlighted StandardFormat nodes (ordered)
    node_ids: Mapped[list[str]] = mapped_column(ARRAY(SAString), nullable=False)

    # Full ancestor heading chain for each highlighted node:
    # [{ node_id, level, text }, ...] — stored so summary doesn't need re-traversal
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
