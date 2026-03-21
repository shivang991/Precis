import uuid
from datetime import datetime
from pydantic import BaseModel


class AncestorNode(BaseModel):
    """Heading ancestor entry stored with each highlight for summary reconstruction."""
    node_id: str
    level: int
    text: str


class HighlightCreate(BaseModel):
    node_ids: list[str]                  # IDs of selected StandardFormat nodes
    color: str = "yellow"
    note: str | None = None


class HighlightRead(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    node_ids: list[str]
    ancestor_node_ids: list[str]
    note: str | None = None
    color: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class HighlightUpdate(BaseModel):
    note: str | None = None
    color: str | None = None


class SummaryView(BaseModel):
    """
    Derived view: the subset of a document's Standard Format that falls
    under highlighted content, including ancestor heading chains.
    """
    document_id: uuid.UUID
    document_title: str
    sections: list[dict]   # Reconstructed tree segments with heading context
