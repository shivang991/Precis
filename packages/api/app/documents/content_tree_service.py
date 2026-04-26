"""
Document Content Tree service — all operations that read or mutate
the document content tree live here.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .models import (
    DocumentNode,
    ImageContent,
    NodeType,
    TableContent,
    TextContent,
)
from .schemas import (
    DocumentContentTreeNode,
    ImageContentPayload,
    NodeContent,
    TableContentPayload,
    TextContentPayload,
)


class DocumentContentTreeService:
    # ── Node creation ────────────────────────────────────────────────────────

    @staticmethod
    def make_node(
        content: NodeContent,
        children: list[DocumentContentTreeNode] | None = None,
    ) -> DocumentContentTreeNode:
        return DocumentContentTreeNode(
            id=str(uuid.uuid4()),
            content=content,
            children=children or [],
        )

    # ── Tree shaping (pure) ──────────────────────────────────────────────────

    @staticmethod
    def nest(
        flat_nodes: list[DocumentContentTreeNode],
    ) -> list[DocumentContentTreeNode]:
        """Nest a flat list of nodes into a tree based on heading levels."""
        root: list[DocumentContentTreeNode] = []
        stack: list[tuple[int, DocumentContentTreeNode | dict]] = [
            (0, {"children": root})
        ]
        for node in flat_nodes:
            heading_level = (
                node.content.level
                if isinstance(node.content, TextContentPayload)
                and node.content.level is not None
                else None
            )
            level = heading_level if heading_level is not None else 999
            while len(stack) > 1 and stack[-1][0] >= level:
                stack.pop()
            parent = stack[-1][1]
            if isinstance(parent, dict):
                parent["children"].append(node)
            else:
                parent.children.append(node)
            if heading_level is not None:
                stack.append((level, node))
        return root

    # ── Persistence ──────────────────────────────────────────────────────────

    @staticmethod
    def _build_content_row(
        node_id: uuid.UUID, content: NodeContent
    ) -> TextContent | TableContent | ImageContent:
        if isinstance(content, TextContentPayload):
            return TextContent(node_id=node_id, text=content.text, level=content.level)
        if isinstance(content, TableContentPayload):
            return TableContent(
                node_id=node_id, rows=content.rows, headers=content.headers
            )
        return ImageContent(
            node_id=node_id, storage_key=content.storage_key, alt=content.alt
        )

    @classmethod
    async def create_nodes(
        cls,
        db: AsyncSession,
        document_id: uuid.UUID,
        nested_nodes: list[DocumentContentTreeNode],
    ) -> None:
        """Flatten a nested tree (DFS) and bulk-insert as document_nodes rows."""
        node_rows: list[DocumentNode] = []
        content_rows: list[TextContent | TableContent | ImageContent] = []
        seq = 0

        def walk(
            nodes: list[DocumentContentTreeNode], parent_id: uuid.UUID | None
        ) -> None:
            nonlocal seq
            for n in nodes:
                node_id = uuid.UUID(n.id)
                node_rows.append(
                    DocumentNode(
                        id=node_id,
                        document_id=document_id,
                        parent_id=parent_id,
                        seq=seq,
                        type=NodeType(n.content.type),
                    )
                )
                content_rows.append(cls._build_content_row(node_id, n.content))
                seq += 1
                walk(n.children, node_id)

        walk(nested_nodes, None)
        db.add_all(node_rows)
        await db.flush()
        db.add_all(content_rows)
        await db.flush()

    @classmethod
    async def build_tree(
        cls, db: AsyncSession, document_id: uuid.UUID
    ) -> list[DocumentContentTreeNode]:
        """Load all nodes for a document and assemble the nested response tree."""
        result = await db.execute(
            select(DocumentNode)
            .where(DocumentNode.document_id == document_id)
            .order_by(DocumentNode.seq)
            .options(
                selectinload(DocumentNode.text_content),
                selectinload(DocumentNode.table_content),
                selectinload(DocumentNode.image_content),
            )
        )
        rows = list(result.scalars().all())

        node_map: dict[uuid.UUID, DocumentContentTreeNode] = {}
        roots: list[DocumentContentTreeNode] = []
        for row in rows:
            node = DocumentContentTreeNode(
                id=str(row.id),
                content=cls._content_to_payload(row),
                children=[],
            )
            node_map[row.id] = node
            if row.parent_id is None:
                roots.append(node)
            else:
                parent = node_map.get(row.parent_id)
                if parent is not None:
                    parent.children.append(node)
        return roots

    @staticmethod
    def _content_to_payload(row: DocumentNode) -> NodeContent:
        if row.type == NodeType.text:
            c = row.text_content
            assert c is not None
            return TextContentPayload(text=c.text, level=c.level)
        if row.type == NodeType.table:
            c = row.table_content
            assert c is not None
            return TableContentPayload(rows=c.rows, headers=c.headers)
        c = row.image_content
        assert c is not None
        return ImageContentPayload(storage_key=c.storage_key, alt=c.alt)

    # ── Mutation ─────────────────────────────────────────────────────────────

    @classmethod
    async def apply_updates(
        cls,
        db: AsyncSession,
        document_id: uuid.UUID,
        updates: dict[str, dict],
    ) -> None:
        """Apply partial content updates to nodes matched by ID. Tree shape and
        node type are immutable — only fields within the matching content row
        are patched."""
        if not updates:
            return
        node_ids = [uuid.UUID(nid) for nid in updates]
        result = await db.execute(
            select(DocumentNode)
            .where(
                DocumentNode.document_id == document_id,
                DocumentNode.id.in_(node_ids),
            )
            .options(
                selectinload(DocumentNode.text_content),
                selectinload(DocumentNode.table_content),
                selectinload(DocumentNode.image_content),
            )
        )
        allowed_fields: dict[NodeType, tuple[str, ...]] = {
            NodeType.text: ("text", "level"),
            NodeType.table: ("rows", "headers"),
            NodeType.image: ("storage_key", "alt"),
        }
        for row in result.scalars().all():
            patch = updates.get(str(row.id), {})
            content_patch = patch.get("content") or {}
            target = row.content
            if target is None:
                continue
            for field in allowed_fields[row.type]:
                if field in content_patch:
                    setattr(target, field, content_patch[field])
        await db.flush()
