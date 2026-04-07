import uuid
from datetime import datetime
from pydantic import BaseModel
from app.documents.models import DocumentStatus, DocumentSource
from app.document_content_tree.schemas import StandardFormatNode, StandardFormat


# ── Document CRUD schemas ─────────────────────────────────────────────────────

class DocumentBase(BaseModel):
    title: str
    theme: str | None = None
    include_headings_in_summary: bool | None = None


class DocumentRead(DocumentBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    original_filename: str
    source: DocumentSource
    status: DocumentStatus
    error_message: str | None = None
    page_count: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentReadWithContent(DocumentRead):
    standard_format: StandardFormat | None = None


class DocumentUpdateSettings(BaseModel):
    title: str | None = None
    theme: str | None = None
    include_headings_in_summary: bool | None = None


class DocumentUpdateContent(BaseModel):
    """Used by the WYSIWYG editor to patch individual nodes."""
    nodes: list[StandardFormatNode]
