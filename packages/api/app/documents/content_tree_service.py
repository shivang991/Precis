"""
Document Content Tree service — all operations that read or mutate
the document content tree live here.
"""

import uuid

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .models import DocumentNode, NodeType
from .schemas import DocumentContentTreeNode


class DocumentContentTreeService:
    # ── Node creation ────────────────────────────────────────────────────────

    @staticmethod
    def make_node(
        node_type: NodeType,
        text: str | None = None,
        level: int | None = None,
        content: dict | None = None,
        page: int | None = None,
        children: list[DocumentContentTreeNode] | None = None,
    ) -> DocumentContentTreeNode:
        return DocumentContentTreeNode(
            id=str(uuid.uuid4()),
            type=node_type,
            level=level,
            text=text,
            content=content,
            page=page,
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
            level = node.level if node.type == NodeType.heading else 999
            while len(stack) > 1 and stack[-1][0] >= level:
                stack.pop()
            parent = stack[-1][1]
            if isinstance(parent, dict):
                parent["children"].append(node)
            else:
                parent.children.append(node)
            if node.type == NodeType.heading:
                stack.append((level, node))
        return root

    # ── Persistence ──────────────────────────────────────────────────────────

    @classmethod
    async def create_nodes(
        cls,
        db: AsyncSession,
        document_id: uuid.UUID,
        nested_nodes: list[DocumentContentTreeNode],
    ) -> None:
        """Flatten a nested tree (DFS) and bulk-insert as document_nodes rows."""
        rows: list[DocumentNode] = []
        seq = 0

        def walk(
            nodes: list[DocumentContentTreeNode], parent_id: uuid.UUID | None
        ) -> None:
            nonlocal seq
            for n in nodes:
                node_id = uuid.UUID(n.id)
                rows.append(
                    DocumentNode(
                        id=node_id,
                        document_id=document_id,
                        parent_id=parent_id,
                        seq=seq,
                        type=n.type,
                        level=n.level,
                        text=n.text,
                        content=n.content,
                        page=n.page,
                    )
                )
                seq += 1
                walk(n.children, node_id)

        walk(nested_nodes, None)
        db.add_all(rows)
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
        )
        rows = list(result.scalars().all())

        node_map: dict[uuid.UUID, DocumentContentTreeNode] = {}
        roots: list[DocumentContentTreeNode] = []
        for row in rows:
            node = DocumentContentTreeNode(
                id=str(row.id),
                type=row.type,
                level=row.level,
                text=row.text,
                content=row.content,
                page=row.page,
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

    # ── Mutation ─────────────────────────────────────────────────────────────

    @classmethod
    async def apply_updates(
        cls,
        db: AsyncSession,
        document_id: uuid.UUID,
        updates: dict[str, dict],
    ) -> None:
        """Apply partial updates to nodes matched by ID. Tree shape is immutable."""
        if not updates:
            return
        node_ids = [uuid.UUID(nid) for nid in updates]
        result = await db.execute(
            select(DocumentNode).where(
                DocumentNode.document_id == document_id,
                DocumentNode.id.in_(node_ids),
            )
        )
        mutable_fields = ("type", "level", "text", "content", "page")
        for row in result.scalars().all():
            patch = updates.get(str(row.id), {})
            for field in mutable_fields:
                if field in patch:
                    setattr(row, field, patch[field])
        await db.flush()
