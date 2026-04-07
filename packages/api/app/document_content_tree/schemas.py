from datetime import datetime
from pydantic import BaseModel


class StandardFormatNode(BaseModel):
    """
    A single node in the Standard Format tree.

    type values:
      heading   – section heading (level 1–6)
      paragraph – body text
      list_item – bullet / numbered list item
      table     – table block (cells stored as nested rows/cols in `content`)
      image     – image block (storage key in `src`)
      code      – code block
    """
    id: str                        # UUID string, stable across edits
    type: str                      # heading | paragraph | list_item | table | image | code
    level: int | None = None       # Only for heading nodes (1–6)
    text: str | None = None        # Plain-text content of the node
    content: dict | None = None    # Rich content (tables, image metadata, etc.)
    page: int | None = None        # Source page number in the original PDF
    children: list["StandardFormatNode"] = []

    model_config = {"from_attributes": True}

StandardFormatNode.model_rebuild()


class StandardFormatMeta(BaseModel):
    title: str
    author: str | None = None
    page_count: int
    source: str
    created_at: datetime


class StandardFormat(BaseModel):
    """
    The full Standard Format document — stored as JSONB in the DB.
    This is the internal representation every view and export is derived from.
    """
    version: str = "1.0"
    meta: StandardFormatMeta
    nodes: list[StandardFormatNode]
    theme: str = "default"
