import uuid
from datetime import datetime

from pydantic import BaseModel

from .models import DocumentSource, DocumentStatus, NodeType

# ── Document content tree schemas ─────────────────────────────────────────────


class DocumentContentTreeNode(BaseModel):
    """A single node in the document content tree."""

    id: str
    type: NodeType
    level: int | None = None
    text: str | None = None
    content: dict | None = None
    page: int | None = None
    children: list["DocumentContentTreeNode"] = []

    model_config = {"from_attributes": True}


DocumentContentTreeNode.model_rebuild()


# ── Document CRUD schemas ─────────────────────────────────────────────────────


class DocumentBase(BaseModel):
    title: str


class DocumentRead(DocumentBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    original_filename: str
    source: DocumentSource
    status: DocumentStatus
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentReadWithContent(DocumentRead):
    document_content_tree: list[DocumentContentTreeNode] | None = None


class DocumentUpdateSettings(BaseModel):
    title: str | None = None


class DocumentUpdateContent(BaseModel):
    """Used by the WYSIWYG editor to patch individual nodes."""

    nodes: list[DocumentContentTreeNode]
