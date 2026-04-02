"""
PDF extraction — single public entry point for both digital and scanned PDFs.

Replaces direct use of pdf_processor.process_digital_pdf and
ocr_processor.process_scanned_pdf. Strategy selection, nesting, and threshold
management are internal to this module.
"""

import io
from dataclasses import dataclass, field

import pdfplumber
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes

from app.documents.models import DocumentSource
from app.shared.standard_format import make_node
from app.shared.config import get_settings


# ── Config dataclasses ────────────────────────────────────────────────────────

@dataclass
class DigitalExtractionConfig:
    """Font-size thresholds for heading detection in native PDFs.
    Each entry is (min_size_pt, heading_level). Evaluated top-to-bottom;
    first match wins."""
    heading_size_map: list[tuple[float, int]] = field(default_factory=lambda: [
        (28, 1), (22, 2), (18, 3), (15, 4), (13, 5), (11, 6),
    ])


@dataclass
class OcrExtractionConfig:
    """Pixel-height thresholds for heading detection in scanned PDFs."""
    dpi: int = 300
    ocr_language: str = ""  # empty = read from settings at call time
    min_confidence: int = 40
    heading_height_map: list[tuple[int, int]] = field(default_factory=lambda: [
        (55, 1), (42, 2), (32, 3),
    ])


# ── Public result type ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ExtractionResult:
    nodes: list[dict]
    page_count: int


# ── Public API ────────────────────────────────────────────────────────────────

def extract_pdf(
    pdf_bytes: bytes,
    source: DocumentSource,
    *,
    digital_config: DigitalExtractionConfig | None = None,
    ocr_config: OcrExtractionConfig | None = None,
) -> ExtractionResult:
    """
    Extract structured content from a PDF.

    Strategy is selected automatically from `source`. Config objects are
    optional; omitting them uses calibrated defaults.
    """
    if source == DocumentSource.DIGITAL:
        cfg = digital_config or DigitalExtractionConfig()
        nodes, page_count = _extract_digital(pdf_bytes, cfg)
    else:
        cfg = ocr_config or OcrExtractionConfig()
        nodes, page_count = _extract_scanned(pdf_bytes, cfg)

    return ExtractionResult(nodes=_nest_nodes_by_heading(nodes), page_count=page_count)


# ── Internal: digital extraction ─────────────────────────────────────────────

def _extract_digital(
    pdf_bytes: bytes, cfg: DigitalExtractionConfig
) -> tuple[list[dict], int]:
    nodes: list[dict] = []

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        page_count = len(pdf.pages)

        for page_num, page in enumerate(pdf.pages, start=1):
            words = page.extract_words(extra_attrs=["size", "fontname"])
            if not words:
                continue

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
                heading_level = _font_size_to_heading_level(avg_size, cfg.heading_size_map)

                if heading_level:
                    nodes.append(make_node("heading", text=text, level=heading_level, page=page_num))
                else:
                    nodes.append(make_node("paragraph", text=text, page=page_num))

            for table in page.extract_tables():
                if table:
                    nodes.append(make_node("table", page=page_num, content={"rows": table}))

    return nodes, page_count


def _font_size_to_heading_level(
    size: float, size_map: list[tuple[float, int]]
) -> int | None:
    for threshold, level in size_map:
        if size >= threshold:
            return level
    return None


# ── Internal: OCR extraction ──────────────────────────────────────────────────

def _extract_scanned(
    pdf_bytes: bytes, cfg: OcrExtractionConfig
) -> tuple[list[dict], int]:
    lang = cfg.ocr_language or get_settings().ocr_language
    images: list[Image.Image] = convert_from_bytes(pdf_bytes, dpi=cfg.dpi)
    page_count = len(images)
    flat_nodes: list[dict] = []

    for page_num, image in enumerate(images, start=1):
        data = pytesseract.image_to_data(
            image,
            lang=lang,
            output_type=pytesseract.Output.DICT,
        )

        n = len(data["text"])
        for i in range(n):
            text = data["text"][i].strip()
            conf = int(data["conf"][i])
            if not text or conf < cfg.min_confidence:
                continue

            height = data["height"][i]
            flat_nodes.append(_classify_ocr_line(text, height, page_num, cfg.heading_height_map))

    return flat_nodes, page_count


def _classify_ocr_line(
    text: str,
    height: int,
    page: int,
    height_map: list[tuple[int, int]],
) -> dict:
    for threshold, level in height_map:
        if height >= threshold:
            return make_node("heading", text=text, level=level, page=page)
    return make_node("paragraph", text=text, page=page)


# ── Internal: nesting ─────────────────────────────────────────────────────────

def _nest_nodes_by_heading(flat_nodes: list[dict]) -> list[dict]:
    """Convert a flat node list into a hierarchy keyed on heading levels."""
    root: list[dict] = []
    stack: list[tuple[int, dict]] = [(0, {"children": root})]

    for node in flat_nodes:
        level = node.get("level") if node["type"] == "heading" else 999

        while len(stack) > 1 and stack[-1][0] >= level:
            stack.pop()

        stack[-1][1]["children"].append(node)

        if node["type"] == "heading":
            stack.append((level, node))

    return root
