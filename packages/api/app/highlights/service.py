import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.documents import DocumentService
from app.documents.models import DocumentNode, DocumentStatus, NodeType
from app.users import User

from .errors import (
    DocumentNotReadyError,
    HighlightNotFoundError,
    HighlightTypeMismatchError,
    NodeNotFoundError,
)
from .handlers import HighlightHandler, TextHighlightHandler
from .models import TextHighlight
from .schemas import HighlightCreate, TextHighlightCreate


class HighlightService:
    def __init__(
        self,
        db: AsyncSession,
        document_service: DocumentService,
    ) -> None:
        self.db = db
        self.document_service = document_service
        self.handlers: dict[NodeType, HighlightHandler[Any, Any]] = {
            NodeType.text: TextHighlightHandler(),
        }

    async def _get_owned_doc(self, document_id: uuid.UUID, user: User) -> None:
        doc = await self.document_service.get_document(document_id, user)
        if doc.status != DocumentStatus.READY:
            raise DocumentNotReadyError()

    async def list_highlights(
        self,
        document_id: uuid.UUID,
        user: User,
    ) -> list[Any]:
        await self._get_owned_doc(document_id, user)
        rows: list[Any] = []
        for handler in self.handlers.values():
            result = await self.db.execute(
                select(handler.model).where(handler.model.document_id == document_id)
            )
            rows.extend(result.scalars().all())
        rows.sort(key=lambda r: r.created_at)
        return rows

    async def add_highlights(
        self,
        document_id: uuid.UUID,
        bodies: list[HighlightCreate],
        user: User,
    ) -> list[Any]:
        await self._get_owned_doc(document_id, user)

        node_ids = {b.node_id for b in bodies}
        if not node_ids:
            return []

        nodes_result = await self.db.execute(
            select(DocumentNode).where(
                DocumentNode.id.in_(node_ids),
                DocumentNode.document_id == document_id,
            )
        )
        nodes_by_id = {n.id: n for n in nodes_result.scalars().all()}

        # Validate types and group payloads by handler.
        by_node_type: dict[NodeType, list[Any]] = {}
        for body in bodies:
            node = nodes_by_id.get(body.node_id)
            if node is None:
                raise NodeNotFoundError()
            handler = self.handlers.get(node.type)
            if handler is None or body.type != handler.node_type.value:
                raise HighlightTypeMismatchError()
            by_node_type.setdefault(node.type, []).append(body)

        created: list[Any] = []
        for node_type, group in by_node_type.items():
            handler = self.handlers[node_type]
            touched_node_ids = {b.node_id for b in group}
            existing_result = await self.db.execute(
                select(handler.model).where(
                    handler.model.document_id == document_id,
                    handler.model.node_id.in_(touched_node_ids),
                )
            )
            existing_rows = list(existing_result.scalars().all())
            existing = [handler.to_existing(r) for r in existing_rows]
            existing_by_id = {
                e.id: r for e, r in zip(existing, existing_rows, strict=True)
            }

            outcome = handler.reconcile(existing, group)

            for hid in outcome.to_delete:
                row = existing_by_id.get(hid)
                if row is not None:
                    await self.db.delete(row)
            await self.db.flush()

            for payload in outcome.to_create:
                row = handler.model(document_id=document_id, **payload)
                self.db.add(row)
                created.append(row)

        await self.db.flush()
        for row in created:
            await self.db.refresh(row)
        return created

    async def remove_highlights(
        self,
        document_id: uuid.UUID,
        highlight_ids: list[uuid.UUID],
        user: User,
    ) -> None:
        await self._get_owned_doc(document_id, user)
        if not highlight_ids:
            return

        found_ids: set[uuid.UUID] = set()
        rows_to_delete: list[Any] = []
        for handler in self.handlers.values():
            result = await self.db.execute(
                select(handler.model).where(
                    handler.model.id.in_(highlight_ids),
                    handler.model.document_id == document_id,
                )
            )
            for row in result.scalars().all():
                found_ids.add(row.id)
                rows_to_delete.append(row)

        if found_ids != set(highlight_ids):
            raise HighlightNotFoundError()

        for row in rows_to_delete:
            await self.db.delete(row)


__all__ = [
    "HighlightService",
    "TextHighlight",
    "TextHighlightCreate",
]
