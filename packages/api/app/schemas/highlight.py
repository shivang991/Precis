import uuid
from datetime import datetime
from pydantic import BaseModel


class HighlightCreate(BaseModel):
    node_id: str                     # ID of the StandardFormat node being highlighted
    start_offset: int | None = None  # Character offset start (None = whole node)
    end_offset: int | None = None    # Character offset end (None = whole node)
    color: str = "yellow"
    note: str | None = None


class HighlightRead(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    node_id: str
    start_offset: int | None
    end_offset: int | None
    ancestor_node_ids: list[str]
    note: str | None = None
    color: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class HighlightUpdate(BaseModel):
    note: str | None = None
    color: str | None = None


class SummarySection(BaseModel):
    """A single highlighted passage with its ancestor heading context."""
    highlight_id: str
    color: str
    note: str | None
    ancestors: list[dict]  # [{ node_id, level, text }, ...]
    text: str              # Highlighted text (sliced by offsets if present)


class SummaryView(BaseModel):
    """
    Derived view: the highlighted passages from a document, each with its
    ancestor heading chain for context.
    """
    document_id: uuid.UUID
    document_title: str
    sections: list[SummarySection]
