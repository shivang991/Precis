import uuid
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.documents import DocumentService
from app.shared import get_db
from app.users import User

from .errors import (
    DocumentNotReadyError,
    HighlightNotFoundError,
)
from .models import Highlight
from .schemas import HighlightCreate


class HighlightService:
    def __init__(
        self,
        db: AsyncSession = Depends(get_db),
        document_service: DocumentService = Depends(DocumentService),
    ) -> None:
        self.db = db
        self.document_service = document_service

    async def _get_owned_doc(self, document_id: uuid.UUID, user: User) -> None:
        doc = await self.document_service.get_document(document_id, user)
        if doc.document_content_tree is None:
            raise DocumentNotReadyError()

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

    def _flatten_highlights(
        self,
        highlights: list[HighlightCreate],
    ) -> list[HighlightCreate]:
        if not highlights:
            return []

        groups: dict[tuple[str, str | None], list[HighlightCreate]] = {}
        result: list[HighlightCreate] = []

        for h in highlights:
            if h.start_offset is not None and h.end_offset is not None:
                groups.setdefault((h.node_id, h.note), []).append(h)
            else:
                result.append(h)

        for (node_id, note), group in groups.items():
            sorted_group = sorted(group, key=lambda h: h.start_offset)
            first = sorted_group[0]
            assert first.start_offset is not None and first.end_offset is not None
            merged_start = first.start_offset
            merged_end = first.end_offset
            for h in sorted_group[1:]:
                assert h.start_offset is not None and h.end_offset is not None
                if h.start_offset <= merged_end:
                    merged_end = max(merged_end, h.end_offset)
                else:
                    result.append(
                        HighlightCreate(
                            node_id=node_id,
                            start_offset=merged_start,
                            end_offset=merged_end,
                            note=note,
                        )
                    )
                    merged_start = h.start_offset
                    merged_end = h.end_offset
            result.append(
                HighlightCreate(
                    node_id=node_id,
                    start_offset=merged_start,
                    end_offset=merged_end,
                    note=note,
                )
            )

        return result

    async def add_highlights(
        self,
        document_id: uuid.UUID,
        bodies: list[HighlightCreate],
        user: User,
    ) -> list[Highlight]:
        await self._get_owned_doc(document_id, user)

        node_ids = {b.node_id for b in bodies}
        result = await self.db.execute(
            select(Highlight).where(
                Highlight.document_id == document_id,
                Highlight.node_id.in_(node_ids),
            )
        )
        existing = list(result.scalars().all())

        existing_as_create = [
            HighlightCreate(
                node_id=h.node_id,
                start_offset=h.start_offset,
                end_offset=h.end_offset,
                note=h.note,
            )
            for h in existing
        ]

        flattened = self._flatten_highlights(existing_as_create + bodies)

        for h in existing:
            await self.db.delete(h)
        await self.db.flush()

        created: list[Highlight] = []
        for body in flattened:
            highlight = Highlight(
                document_id=document_id,
                node_id=body.node_id,
                start_offset=body.start_offset,
                end_offset=body.end_offset,
                note=body.note,
            )
            self.db.add(highlight)
            created.append(highlight)
        await self.db.flush()
        for h in created:
            await self.db.refresh(h)
        return created

    async def remove_highlights(
        self,
        document_id: uuid.UUID,
        highlight_ids: list[uuid.UUID],
        user: User,
    ) -> None:
        await self._get_owned_doc(document_id, user)
        result = await self.db.execute(
            select(Highlight).where(
                Highlight.id.in_(highlight_ids),
                Highlight.document_id == document_id,
            )
        )
        found = list(result.scalars().all())
        if len(found) != len(highlight_ids):
            raise HighlightNotFoundError()
        for highlight in found:
            await self.db.delete(highlight)
