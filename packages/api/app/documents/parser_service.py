import io
from dataclasses import dataclass

import pdfplumber
import pytesseract
from pdf2image import convert_from_bytes

from app.shared import get_settings

from .content_tree_service import DocumentContentTreeService
from .schemas import (
    DocumentContentTreeNode,
    TableContentPayload,
    TextContentPayload,
)

settings = get_settings()


@dataclass(frozen=True)
class ParsedPDF:
    nodes: list[DocumentContentTreeNode]
    page_count: int


def _make_text_node(text: str, level: int | None) -> DocumentContentTreeNode:
    return DocumentContentTreeService.make_node(
        TextContentPayload(text=text, level=level)
    )


def _make_table_node(rows: list) -> DocumentContentTreeNode:
    return DocumentContentTreeService.make_node(TableContentPayload(rows=rows))


class ParserService:
    # ── Configuration ─────────────────────────────────────────────────────────────

    digital_pdf_heading_size_map: list[tuple[float, int]] = [
        (28, 1),
        (22, 2),
        (18, 3),
        (15, 4),
        (13, 5),
        (11, 6),
    ]

    ocr_dpi: int = 300
    ocr_min_confidence: int = 40
    ocr_heading_height_map: list[tuple[int, int]] = [
        (55, 1),
        (42, 2),
        (32, 3),
    ]
    ocr_lang = settings.ocr_language

    # –– Digital PDFs ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––

    def parse_digital_pdf(self, pdf_bytes: bytes) -> ParsedPDF:
        nodes: list[DocumentContentTreeNode] = []

        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            page_count = len(pdf.pages)

            for page in pdf.pages:
                words = page.extract_words(extra_attrs=["size", "fontname"])
                if not words:
                    continue

                lines: dict[float, list[dict]] = {}
                for word in words:
                    y = round(word["top"], 1)
                    lines.setdefault(y, []).append(word)

                # Walk lines top-to-bottom, classifying each word by its own
                # font size.  Consecutive same-type words merge into one node;
                # a new node starts only on type change or a "double newline"
                # (vertical gap between lines that exceeds the current line height).
                sorted_ys = sorted(lines)
                prev_line_bottom: float | None = None

                for y in sorted_ys:
                    line_words = lines[y]
                    line_top = min(w["top"] for w in line_words)
                    line_bottom = max(w["bottom"] for w in line_words)
                    line_height = line_bottom - line_top

                    has_double_newline = (
                        prev_line_bottom is not None
                        and line_height > 0
                        and (line_top - prev_line_bottom) > line_height
                    )

                    for word in line_words:
                        text = word["text"].strip()
                        if not text:
                            continue

                        heading_level = self._font_size_to_heading_level(
                            word.get("size", 10)
                        )

                        can_merge = False
                        if nodes and not has_double_newline:
                            last = nodes[-1]
                            if isinstance(last.content, TextContentPayload):
                                if last.content.level == heading_level:
                                    can_merge = True

                        if can_merge:
                            last_content = nodes[-1].content
                            assert isinstance(last_content, TextContentPayload)
                            last_content.text += " " + text
                        else:
                            nodes.append(_make_text_node(text, heading_level))

                        has_double_newline = False

                    prev_line_bottom = line_bottom

                for table in page.extract_tables():
                    if table:
                        nodes.append(_make_table_node(table))

        return ParsedPDF(nodes=nodes, page_count=page_count)

    def _font_size_to_heading_level(self, size: float) -> int | None:
        for threshold, level in self.digital_pdf_heading_size_map:
            if size >= threshold:
                return level
        return None

    # –– Scanned PDFs ––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––

    def parse_scanned_pdf(self, pdf_bytes: bytes) -> ParsedPDF:
        images = convert_from_bytes(pdf_bytes, dpi=self.ocr_dpi)
        page_count = len(images)
        nodes: list[DocumentContentTreeNode] = []

        for image in images:
            data = pytesseract.image_to_data(
                image,
                lang=self.ocr_lang,
                output_type=pytesseract.Output.DICT,
            )

            # Tesseract groups words into blocks → paragraphs → lines.
            # A change in block_num or par_num is the OCR equivalent of a
            # double newline, so we use it to force a node break.
            n = len(data["text"])
            prev_block: int | None = None
            prev_par: int | None = None

            for i in range(n):
                text = data["text"][i].strip()
                conf = int(data["conf"][i])
                if not text or conf < self.ocr_min_confidence:
                    continue

                height = data["height"][i]
                block_num = data["block_num"][i]
                par_num = data["par_num"][i]

                has_paragraph_break = prev_block is not None and (
                    block_num != prev_block or par_num != prev_par
                )

                heading_level = self._ocr_height_to_heading_level(height)

                can_merge = False
                if nodes and not has_paragraph_break:
                    last = nodes[-1]
                    if isinstance(last.content, TextContentPayload):
                        if last.content.level == heading_level:
                            can_merge = True

                if can_merge:
                    last_content = nodes[-1].content
                    assert isinstance(last_content, TextContentPayload)
                    last_content.text += " " + text
                else:
                    nodes.append(_make_text_node(text, heading_level))

                prev_block = block_num
                prev_par = par_num

        return ParsedPDF(nodes=nodes, page_count=page_count)

    def _ocr_height_to_heading_level(self, height: int) -> int | None:
        for threshold, level in self.ocr_heading_height_map:
            if height >= threshold:
                return level
        return None
