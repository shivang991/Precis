import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel


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


# Discriminated unions on `type` — currently single-variant; adding the
# table/image variants is a one-line change once those handlers exist.
HighlightCreate = TextHighlightCreate
HighlightRead = TextHighlightRead
