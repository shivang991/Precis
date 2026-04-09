"""
Document Content Tree service — all operations that read or mutate
the document content tree live here.
"""

import uuid
from datetime import datetime, timezone

from app.document_content_tree.schemas import DocumentContentTreeNode


class DocumentContentTreeService:

    # ── Node creation ────────────────────────────────────────────────────────

    @staticmethod
    def make_node(
        node_type: str,
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

    # ── Full-document builder ────────────────────────────────────────────────

    @staticmethod
    def build_document(
        *,
        title: str,
        nodes: list[DocumentContentTreeNode],
        source: str,
        page_count: int,
        author: str | None = None,
        theme: str = "default",
    ) -> dict:
        """Build the full document content tree JSONB dict for DB storage."""
        return {
            "version": "1.0",
            "meta": {
                "title": title,
                "author": author,
                "page_count": page_count,
                "source": source,
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            "nodes": [n.model_dump() for n in nodes],
            "theme": theme,
        }

    # ── Serialisation boundary ───────────────────────────────────────────────

    @staticmethod
    def parse_nodes(raw_nodes: list[dict]) -> list[DocumentContentTreeNode]:
        """Parse raw JSONB node dicts into typed DocumentContentTreeNode objects."""
        return [DocumentContentTreeNode.model_validate(n) for n in raw_nodes]

    # ── Tree traversal ───────────────────────────────────────────────────────

    @staticmethod
    def flatten(nodes: list[DocumentContentTreeNode]) -> list[DocumentContentTreeNode]:
        """Depth-first flattening of the node tree."""
        result: list[DocumentContentTreeNode] = []
        for node in nodes:
            result.append(node)
            result.extend(DocumentContentTreeService.flatten(node.children))
        return result

    @staticmethod
    def build_node_index(document_content_tree: dict) -> dict[str, DocumentContentTreeNode]:
        """Build a flat {node_id: node} lookup from the raw JSONB dict."""
        svc = DocumentContentTreeService
        nodes = svc.parse_nodes(document_content_tree.get("nodes", []))
        return {n.id: n for n in svc.flatten(nodes)}

    # ── Tree mutation ────────────────────────────────────────────────────────

    @staticmethod
    def nest(flat_nodes: list[DocumentContentTreeNode]) -> list[DocumentContentTreeNode]:
        """Nest a flat list of nodes into a tree based on heading levels."""
        root: list[DocumentContentTreeNode] = []
        stack: list[tuple[int, DocumentContentTreeNode | dict]] = [(0, {"children": root})]
        for node in flat_nodes:
            level = node.level if node.type == "heading" else 999
            while len(stack) > 1 and stack[-1][0] >= level:
                stack.pop()
            parent = stack[-1][1]
            if isinstance(parent, dict):
                parent["children"].append(node)
            else:
                parent.children.append(node)
            if node.type == "heading":
                stack.append((level, node))
        return root

    @staticmethod
    def patch(
        nodes: list[DocumentContentTreeNode],
        updates: dict[str, dict],
    ) -> list[DocumentContentTreeNode]:
        """Apply partial updates to nodes matched by ID, recursing into children."""
        result: list[DocumentContentTreeNode] = []
        for node in nodes:
            if node.id in updates:
                patched = node.model_copy(update=updates[node.id])
                patched.children = DocumentContentTreeService.patch(node.children, updates)
                result.append(patched)
            else:
                node.children = DocumentContentTreeService.patch(node.children, updates)
                result.append(node)
        return result

    # ── Ancestor resolution ──────────────────────────────────────────────────

    @staticmethod
    def get_ancestor_ids(document_content_tree: dict, node_id: str) -> list[str]:
        """
        Return the IDs of all heading ancestors (root → leaf) for a given node.
        Accepts the raw JSONB document_content_tree dict.
        """
        svc = DocumentContentTreeService
        nodes = svc.parse_nodes(document_content_tree.get("nodes", []))
        all_nodes = svc.flatten(nodes)
        id_to_node = {n.id: n for n in all_nodes}

        parent_map: dict[str, str | None] = {}

        def _walk(nodes: list[DocumentContentTreeNode], parent_id: str | None) -> None:
            for node in nodes:
                parent_map[node.id] = parent_id
                _walk(node.children, node.id)

        _walk(nodes, None)

        chain: list[str] = []
        current = parent_map.get(node_id)
        while current is not None:
            node = id_to_node.get(current)
            if node and node.type == "heading":
                chain.append(current)
            current = parent_map.get(current)

        return list(reversed(chain))
