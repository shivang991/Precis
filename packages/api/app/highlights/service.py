import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.users.models import User
from app.documents.models import Document
from app.highlights.models import Highlight
from app.highlights.schemas import HighlightCreate
from app.highlights.errors import (
    DocumentNotFoundError,
    DocumentNotReadyError,
    HighlightNotFoundError,
)


class HighlightService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def _get_owned_doc(self, document_id: uuid.UUID, user: User) -> Document:
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.owner_id == user.id,
            )
        )
        doc = result.scalar_one_or_none()
        if doc is None:
            raise DocumentNotFoundError()
        if doc.standard_format is None:
            raise DocumentNotReadyError()
        return doc

    async def list_highlights(
        self, document_id: uuid.UUID, user: User
    ) -> list[Highlight]:
        await self._get_owned_doc(document_id, user)
        result = await self.db.execute(
            select(Highlight)
            .where(Highlight.document_id == document_id)
            .order_by(Highlight.created_at)
        )
        return list(result.scalars().all())

    async def add_highlight(
        self, document_id: uuid.UUID, body: HighlightCreate, user: User
    ) -> Highlight:
        await self._get_owned_doc(document_id, user)
        highlight = Highlight(
            document_id=document_id,
            node_id=body.node_id,
            start_offset=body.start_offset,
            end_offset=body.end_offset,
            note=body.note,
        )
        self.db.add(highlight)
        await self.db.flush()
        await self.db.refresh(highlight)
        return highlight

    async def remove_highlight(
        self, document_id: uuid.UUID, highlight_id: uuid.UUID, user: User
    ) -> None:
        await self._get_owned_doc(document_id, user)
        result = await self.db.execute(
            select(Highlight).where(
                Highlight.id == highlight_id,
                Highlight.document_id == document_id,
            )
        )
        highlight = result.scalar_one_or_none()
        if highlight is None:
            raise HighlightNotFoundError()
        await self.db.delete(highlight)
