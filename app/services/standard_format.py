"""
Standard Format — the internal document representation for Precis.

Every PDF (digital or scanned) is normalised into this tree before storage.
The tree is a list of top-level nodes; each node may contain children,
forming a hierarchy that mirrors the document's heading structure.

Node types
----------
heading   – H1–H6 structural heading
paragraph – body text block
list_item – bullet or numbered item
table     – structured table (content holds rows/cols)
image     – embedded image (content holds storage_key, alt, caption)
code      – code block
"""

import uuid
from datetime import datetime, timezone
from typing import Any


# ── Node helpers ──────────────────────────────────────────────────────────────

def make_node(
    node_type: str,
    text: str | None = None,
    level: int | None = None,
    content: dict | None = None,
    page: int | None = None,
    children: list[dict] | None = None,
) -> dict:
    return {
        "id": str(uuid.uuid4()),
        "type": node_type,
        "level": level,
        "text": text,
        "content": content,
        "page": page,
        "children": children or [],
    }


# ── Builder ───────────────────────────────────────────────────────────────────

def build_standard_format(
    *,
    title: str,
    nodes: list[dict],
    source: str,
    page_count: int,
    author: str | None = None,
    theme: str = "default",
) -> dict:
    """
    Wrap a list of nodes into a complete Standard Format document dict.
    This dict is stored as-is in Document.standard_format (JSONB).
    """
    return {
        "version": "1.0",
        "meta": {
            "title": title,
            "author": author,
            "page_count": page_count,
            "source": source,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
        "nodes": nodes,
        "theme": theme,
    }


# ── Ancestor resolution ───────────────────────────────────────────────────────

def _flatten_nodes(nodes: list[dict]) -> list[dict]:
    """Depth-first flattening of the node tree."""
    result = []
    for node in nodes:
        result.append(node)
        result.extend(_flatten_nodes(node.get("children", [])))
    return result


def get_ancestors(standard_format: dict, node_ids: list[str]) -> list[str]:
    """
    Given a list of highlighted node IDs, return the IDs of all heading
    ancestors (from root down) for each node.  Used when creating a Highlight.

    Returns a de-duplicated, ordered list of ancestor node IDs.
    """
    all_nodes = _flatten_nodes(standard_format.get("nodes", []))
    id_to_node = {n["id"]: n for n in all_nodes}

    # Build parent map (child_id → parent_id)
    parent_map: dict[str, str | None] = {}

    def _walk(nodes: list[dict], parent_id: str | None) -> None:
        for node in nodes:
            parent_map[node["id"]] = parent_id
            _walk(node.get("children", []), node["id"])

    _walk(standard_format.get("nodes", []), None)

    seen: set[str] = set()
    ancestor_ids: list[str] = []

    for nid in node_ids:
        chain: list[str] = []
        current = parent_map.get(nid)
        while current is not None:
            node = id_to_node.get(current)
            if node and node["type"] == "heading":
                chain.append(current)
            current = parent_map.get(current)
        for aid in reversed(chain):
            if aid not in seen:
                seen.add(aid)
                ancestor_ids.append(aid)

    return ancestor_ids


# ── Summary reconstruction ────────────────────────────────────────────────────

def build_summary_sections(
    standard_format: dict,
    highlights: list[Any],  # list of Highlight ORM objects
    include_headings: bool = True,
) -> list[dict]:
    """
    Reconstruct the summary view from the Standard Format + highlight records.

    For each highlight, emit a section dict:
      {
        "highlight_id": ...,
        "color": ...,
        "ancestors": [{ id, level, text }, ...],   # heading chain
        "nodes": [{ ... }],                         # highlighted content nodes
      }
    """
    all_nodes = _flatten_nodes(standard_format.get("nodes", []))
    id_to_node = {n["id"]: n for n in all_nodes}

    sections = []
    for h in highlights:
        ancestors = []
        if include_headings:
            for aid in h.ancestor_node_ids:
                ancestor_node = id_to_node.get(aid)
                if ancestor_node:
                    ancestors.append({
                        "node_id": aid,
                        "level": ancestor_node.get("level"),
                        "text": ancestor_node.get("text", ""),
                    })

        content_nodes = [
            id_to_node[nid] for nid in h.node_ids if nid in id_to_node
        ]

        sections.append({
            "highlight_id": str(h.id),
            "color": h.color,
            "note": h.note,
            "ancestors": ancestors,
            "nodes": content_nodes,
        })

    return sections
