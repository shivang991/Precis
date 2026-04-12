import uuid
from datetime import datetime

from pydantic import BaseModel


class HighlightCreate(BaseModel):
    node_id: str
    start_offset: int | None = None
    end_offset: int | None = None
    note: str | None = None


class HighlightRead(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    node_id: str
    start_offset: int | None
    end_offset: int | None
    note: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
