"""
Document Content Tree service — all operations that read or mutate
the Standard Format node tree live here.
"""

import uuid
from datetime import datetime, timezone

from app.document_content_tree.schemas import StandardFormatNode


class DocumentContentTreeService:

    # ── Node creation ────────────────────────────────────────────────────────

    @staticmethod
    def make_node(
        node_type: str,
        text: str | None = None,
        level: int | None = None,
        content: dict | None = None,
        page: int | None = None,
        children: list[StandardFormatNode] | None = None,
    ) -> StandardFormatNode:
        return StandardFormatNode(
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
        nodes: list[StandardFormatNode],
        source: str,
        page_count: int,
        author: str | None = None,
        theme: str = "default",
    ) -> dict:
        """Build the full Standard Format JSONB dict for DB storage."""
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
    def parse_nodes(raw_nodes: list[dict]) -> list[StandardFormatNode]:
        """Parse raw JSONB node dicts into typed StandardFormatNode objects."""
        return [StandardFormatNode.model_validate(n) for n in raw_nodes]

    # ── Tree traversal ───────────────────────────────────────────────────────

    @staticmethod
    def flatten(nodes: list[StandardFormatNode]) -> list[StandardFormatNode]:
        """Depth-first flattening of the node tree."""
        result: list[StandardFormatNode] = []
        for node in nodes:
            result.append(node)
            result.extend(DocumentContentTreeService.flatten(node.children))
        return result

    @staticmethod
    def build_node_index(standard_format: dict) -> dict[str, StandardFormatNode]:
        """Build a flat {node_id: node} lookup from the raw JSONB dict."""
        svc = DocumentContentTreeService
        nodes = svc.parse_nodes(standard_format.get("nodes", []))
        return {n.id: n for n in svc.flatten(nodes)}

    # ── Tree mutation ────────────────────────────────────────────────────────

    @staticmethod
    def nest(flat_nodes: list[StandardFormatNode]) -> list[StandardFormatNode]:
        """Nest a flat list of nodes into a tree based on heading levels."""
        root: list[StandardFormatNode] = []
        stack: list[tuple[int, StandardFormatNode | dict]] = [(0, {"children": root})]
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
        nodes: list[StandardFormatNode],
        updates: dict[str, dict],
    ) -> list[StandardFormatNode]:
        """Apply partial updates to nodes matched by ID, recursing into children."""
        result: list[StandardFormatNode] = []
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
    def get_ancestor_ids(standard_format: dict, node_id: str) -> list[str]:
        """
        Return the IDs of all heading ancestors (root → leaf) for a given node.
        Accepts the raw JSONB standard_format dict.
        """
        svc = DocumentContentTreeService
        nodes = svc.parse_nodes(standard_format.get("nodes", []))
        all_nodes = svc.flatten(nodes)
        id_to_node = {n.id: n for n in all_nodes}

        parent_map: dict[str, str | None] = {}

        def _walk(nodes: list[StandardFormatNode], parent_id: str | None) -> None:
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
