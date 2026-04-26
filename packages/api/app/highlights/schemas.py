import uuid
from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field


class TextHighlightCreate(BaseModel):
    type: Literal["text"] = "text"
    node_id: uuid.UUID
    start_offset: int
    end_offset: int
    note: str | None = None


class TextHighlightRead(BaseModel):
    type: Literal["text"] = "text"
    id: uuid.UUID
    document_id: uuid.UUID
    node_id: uuid.UUID
    start_offset: int
    end_offset: int
    note: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TableHighlightCreate(BaseModel):
    type: Literal["table"] = "table"
    node_id: uuid.UUID
    rows: list[int] = Field(default_factory=list)
    columns: list[int] = Field(default_factory=list)
    note: str | None = None


class TableHighlightRead(BaseModel):
    type: Literal["table"] = "table"
    id: uuid.UUID
    document_id: uuid.UUID
    node_id: uuid.UUID
    rows: list[int]
    columns: list[int]
    note: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ImageHighlightCreate(BaseModel):
    type: Literal["image"] = "image"
    node_id: uuid.UUID


class ImageHighlightRead(BaseModel):
    type: Literal["image"] = "image"
    id: uuid.UUID
    document_id: uuid.UUID
    node_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


HighlightCreate = Annotated[
    TextHighlightCreate | TableHighlightCreate | ImageHighlightCreate,
    Field(discriminator="type"),
]
HighlightRead = Annotated[
    TextHighlightRead | TableHighlightRead | ImageHighlightRead,
    Field(discriminator="type"),
]
