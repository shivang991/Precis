import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from .models import DocumentSource, DocumentStatus

# ── Node content payloads (discriminated by `type`) ───────────────────────────


class TextContentPayload(BaseModel):
    type: Literal["text"] = "text"
    text: str
    level: int | None = None

    model_config = {"from_attributes": True}


class TableContentPayload(BaseModel):
    type: Literal["table"] = "table"
    rows: list
    headers: list | None = None

    model_config = {"from_attributes": True}


class ImageContentPayload(BaseModel):
    type: Literal["image"] = "image"
    storage_key: str
    alt: str | None = None

    model_config = {"from_attributes": True}


NodeContent = Annotated[
    TextContentPayload | TableContentPayload | ImageContentPayload,
    Field(discriminator="type"),
]


# ── Document content tree schemas ─────────────────────────────────────────────


class DocumentContentTreeNode(BaseModel):
    """A single node in the document content tree."""

    id: str
    content: NodeContent
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
