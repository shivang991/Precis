from typing import Any

from app.document_content_tree.service import DocumentContentTreeService


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
        "note": ...,
        "ancestors": [{ node_id, level, text }, ...],
        "text": "...",
      }

    When start_offset / end_offset are set, only the selected character slice is
    included in "text".  Otherwise the full node text is used.
    """
    node_index = DocumentContentTreeService.build_node_index(standard_format)

    sections = []
    for h in highlights:
        ancestors = []
        if include_headings:
            for aid in h.ancestor_node_ids:
                ancestor_node = node_index.get(aid)
                if ancestor_node:
                    ancestors.append({
                        "node_id": aid,
                        "level": ancestor_node.level,
                        "text": ancestor_node.text or "",
                    })

        content_node = node_index.get(h.node_id)
        full_text = (content_node.text or "") if content_node else ""

        if h.start_offset is not None and h.end_offset is not None:
            text = full_text[h.start_offset:h.end_offset]
        else:
            text = full_text

        sections.append({
            "highlight_id": str(h.id),
            "color": h.color,
            "note": h.note,
            "ancestors": ancestors,
            "text": text,
        })

    return sections
