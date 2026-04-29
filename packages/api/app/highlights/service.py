import uuid

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
from .models import ImageHighlight, TableHighlight, TextHighlight
from .schemas import (
    HighlightCreate,
    ImageHighlightCreate,
    TableHighlightCreate,
    TextHighlightCreate,
)

HighlightRow = TextHighlight | TableHighlight | ImageHighlight


class HighlightService:
    _BODY_TYPE_TO_NODE_TYPE: dict[str, NodeType] = {
        "text": NodeType.text,
        "table": NodeType.table,
        "image": NodeType.image,
    }

    def __init__(
        self,
        db: AsyncSession,
        document_service: DocumentService,
    ) -> None:
        self.db = db
        self.document_service = document_service

    # --- Public API ---

    async def list_highlights(
        self,
        document_id: uuid.UUID,
        user: User,
    ) -> list[HighlightRow]:
        await self._assert_doc_ready(document_id, user)
        rows: list[HighlightRow] = []
        for model in (TextHighlight, TableHighlight, ImageHighlight):
            result = await self.db.execute(
                select(model).where(model.document_id == document_id)
            )
            rows.extend(result.scalars().all())
        rows.sort(key=lambda r: r.created_at)
        return rows

    async def add_highlights(
        self,
        document_id: uuid.UUID,
        bodies: list[HighlightCreate],
        user: User,
    ) -> None:
        await self._assert_doc_ready(document_id, user)
        if not bodies:
            return

        node_ids = {b.node_id for b in bodies}
        nodes_result = await self.db.execute(
            select(DocumentNode.id, DocumentNode.type).where(
                DocumentNode.id.in_(node_ids),
                DocumentNode.document_id == document_id,
            )
        )
        node_type_by_id = {nid: ntype for nid, ntype in nodes_result.all()}

        text_bodies: list[TextHighlightCreate] = []
        table_bodies: list[TableHighlightCreate] = []
        image_bodies: list[ImageHighlightCreate] = []
        for body in bodies:
            node_type = node_type_by_id.get(body.node_id)
            if node_type is None:
                raise NodeNotFoundError()
            if self._BODY_TYPE_TO_NODE_TYPE[body.type] != node_type:
                raise HighlightTypeMismatchError()
            if isinstance(body, TextHighlightCreate):
                text_bodies.append(body)
            elif isinstance(body, TableHighlightCreate):
                table_bodies.append(body)
            else:
                image_bodies.append(body)

        if text_bodies:
            await self._add_text(document_id, text_bodies)
        if table_bodies:
            await self._add_table(document_id, table_bodies)
        if image_bodies:
            await self._add_image(document_id, image_bodies)

    async def remove_highlights(
        self,
        document_id: uuid.UUID,
        highlight_ids: list[uuid.UUID],
        user: User,
    ) -> None:
        await self._assert_doc_ready(document_id, user)
        if not highlight_ids:
            return

        found_ids: set[uuid.UUID] = set()
        rows_to_delete: list[HighlightRow] = []
        for model in (TextHighlight, TableHighlight, ImageHighlight):
            result = await self.db.execute(
                select(model).where(
                    model.id.in_(highlight_ids),
                    model.document_id == document_id,
                )
            )
            for row in result.scalars().all():
                found_ids.add(row.id)
                rows_to_delete.append(row)

        if found_ids != set(highlight_ids):
            raise HighlightNotFoundError()

        for row in rows_to_delete:
            await self.db.delete(row)

    # --- Private API ---

    async def _assert_doc_ready(self, document_id: uuid.UUID, user: User) -> None:
        doc = await self.document_service.get_document(document_id, user)
        if doc.status != DocumentStatus.READY:
            raise DocumentNotReadyError()

    async def _add_text(
        self,
        document_id: uuid.UUID,
        bodies: list[TextHighlightCreate],
    ) -> None:
        existing_result = await self.db.execute(
            select(TextHighlight).where(
                TextHighlight.document_id == document_id,
                TextHighlight.node_id.in_({b.node_id for b in bodies}),
            )
        )
        # Group existing rows + incoming bodies by (node_id, note).
        existing_by_group: dict[tuple[uuid.UUID, str | None], list[TextHighlight]] = {}
        for row in existing_result.scalars().all():
            existing_by_group.setdefault((row.node_id, row.note), []).append(row)

        incoming_by_group: dict[tuple[uuid.UUID, str | None], list[tuple[int, int]]] = (
            {}
        )
        for body in bodies:
            incoming_by_group.setdefault((body.node_id, body.note), []).append(
                (body.start_offset, body.end_offset)
            )

        for key, incoming_ranges in incoming_by_group.items():
            group_existing = existing_by_group.get(key, [])
            merged = self._merge_ranges(
                [(r.start_offset, r.end_offset) for r in group_existing]
                + incoming_ranges
            )

            unused_existing = list(group_existing)
            for start, end in merged:
                anchor = self._pick_anchor(unused_existing, start, end)
                if anchor is not None:
                    anchor.start_offset = start
                    anchor.end_offset = end
                    unused_existing.remove(anchor)
                else:
                    self.db.add(
                        TextHighlight(
                            document_id=document_id,
                            node_id=key[0],
                            start_offset=start,
                            end_offset=end,
                            note=key[1],
                        )
                    )

            for row in unused_existing:
                await self.db.delete(row)

    async def _add_table(
        self,
        document_id: uuid.UUID,
        bodies: list[TableHighlightCreate],
    ) -> None:
        touched_node_ids = {b.node_id for b in bodies}
        existing_result = await self.db.execute(
            select(TableHighlight).where(
                TableHighlight.document_id == document_id,
                TableHighlight.node_id.in_(touched_node_ids),
            )
        )
        existing_by_node = {r.node_id: r for r in existing_result.scalars().all()}

        # Last body wins for any duplicate node_id within the same request.
        bodies_by_node: dict[uuid.UUID, TableHighlightCreate] = {
            b.node_id: b for b in bodies
        }
        for node_id, body in bodies_by_node.items():
            row = existing_by_node.get(node_id)
            if row is None:
                self.db.add(
                    TableHighlight(
                        document_id=document_id,
                        node_id=node_id,
                        rows=list(body.rows),
                        columns=list(body.columns),
                        note=body.note,
                    )
                )
                continue
            row.rows = list(body.rows)
            row.columns = list(body.columns)
            row.note = body.note

    async def _add_image(
        self,
        document_id: uuid.UUID,
        bodies: list[ImageHighlightCreate],
    ) -> None:
        touched_node_ids = {b.node_id for b in bodies}
        existing_result = await self.db.execute(
            select(ImageHighlight.node_id).where(
                ImageHighlight.document_id == document_id,
                ImageHighlight.node_id.in_(touched_node_ids),
            )
        )
        existing_node_ids = {nid for (nid,) in existing_result.all()}

        seen: set[uuid.UUID] = set()
        for body in bodies:
            if body.node_id in existing_node_ids or body.node_id in seen:
                continue
            seen.add(body.node_id)
            self.db.add(
                ImageHighlight(document_id=document_id, node_id=body.node_id)
            )

    @staticmethod
    def _merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
        if not ranges:
            return []
        ordered = sorted(ranges, key=lambda r: r[0])
        merged: list[tuple[int, int]] = []
        cur_start, cur_end = ordered[0]
        for start, end in ordered[1:]:
            if start <= cur_end:
                cur_end = max(cur_end, end)
            else:
                merged.append((cur_start, cur_end))
                cur_start, cur_end = start, end
        merged.append((cur_start, cur_end))
        return merged

    @staticmethod
    def _pick_anchor(
        rows: list[TextHighlight], start: int, end: int
    ) -> TextHighlight | None:
        """Earliest-created row whose range overlaps [start, end]."""
        overlapping = [
            r for r in rows if r.start_offset <= end and r.end_offset >= start
        ]
        if not overlapping:
            return None
        return min(overlapping, key=lambda r: r.created_at)
