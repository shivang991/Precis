"""
Digital PDF processor — extracts structured content from native (text-layer) PDFs
using pdfplumber.  Produces a list of Standard Format nodes.
"""

import io
import pdfplumber
from app.services.standard_format import make_node


# Heuristic thresholds for heading detection based on font size.
# Adjust these once you have real documents to calibrate against.
_HEADING_SIZE_MAP = [
    (28, 1),
    (22, 2),
    (18, 3),
    (15, 4),
    (13, 5),
    (11, 6),
]


def _font_size_to_heading_level(size: float) -> int | None:
    for threshold, level in _HEADING_SIZE_MAP:
        if size >= threshold:
            return level
    return None


def process_digital_pdf(pdf_bytes: bytes) -> tuple[list[dict], int]:
    """
    Extract content from a native PDF.

    Returns
    -------
    nodes      : list of Standard Format node dicts (flat; caller nests by heading)
    page_count : total page count
    """
    nodes: list[dict] = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        page_count = len(pdf.pages)

        for page_num, page in enumerate(pdf.pages, start=1):
            words = page.extract_words(extra_attrs=["size", "fontname"])
            if not words:
                continue

            # Group consecutive words into lines by their top-y coordinate
            lines: dict[float, list[dict]] = {}
            for word in words:
                y = round(word["top"], 1)
                lines.setdefault(y, []).append(word)

            for y in sorted(lines):
                line_words = lines[y]
                text = " ".join(w["text"] for w in line_words).strip()
                if not text:
                    continue

                avg_size = sum(w.get("size", 10) for w in line_words) / len(line_words)
                heading_level = _font_size_to_heading_level(avg_size)

                if heading_level:
                    nodes.append(make_node("heading", text=text, level=heading_level, page=page_num))
                else:
                    nodes.append(make_node("paragraph", text=text, page=page_num))

            # Extract tables on this page
            for table in page.extract_tables():
                if table:
                    nodes.append(make_node(
                        "table",
                        page=page_num,
                        content={"rows": table},
                    ))

    return nest_nodes_by_heading(nodes), page_count


def nest_nodes_by_heading(flat_nodes: list[dict]) -> list[dict]:
    """
    Convert a flat list of nodes into a hierarchy where non-heading nodes
    and lower-level headings become children of higher-level headings.
    """
    root: list[dict] = []
    # Stack holds (level, node) pairs; level=0 is the virtual root
    stack: list[tuple[int, dict]] = [(0, {"children": root})]

    for node in flat_nodes:
        level = node.get("level") if node["type"] == "heading" else 999

        # Pop stack entries whose level >= current heading level
        while len(stack) > 1 and stack[-1][0] >= level:
            stack.pop()

        stack[-1][1]["children"].append(node)

        if node["type"] == "heading":
            stack.append((level, node))

    return root
