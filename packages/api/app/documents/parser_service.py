import io
from dataclasses import dataclass
from typing import Annotated

import pdfplumber
import pytesseract
from fastapi import Depends
from PIL import Image
from pdf2image import convert_from_bytes

from app.document_content_tree import DocumentContentTreeNode, DocumentContentTreeService
from app.shared import get_settings


@dataclass(frozen=True)
class ParsedPDF:
    nodes: list[DocumentContentTreeNode]
    page_count: int


class ParserService:

    def __init__(self, tree_svc: Annotated[DocumentContentTreeService, Depends(DocumentContentTreeService)]) -> None:
        self.tree_svc = tree_svc

    # ── Configuration ───────────────────────────────────────────────────────────────────

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

    # –– Digital PDFs –––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––

    def parse_digital_pdf(self, pdf_bytes: bytes) -> ParsedPDF:
        nodes: list[DocumentContentTreeNode] = []

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

                    # Gap between bottom of previous line and top of this line
                    # exceeding the line's own height ≈ a blank line in between.
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
                        node_type = "heading" if heading_level else "paragraph"

                        can_merge = False
                        if nodes and not has_double_newline:
                            last = nodes[-1]
                            if last.type == node_type and last.page == page_num:
                                if node_type == "paragraph":
                                    can_merge = True
                                elif last.level == heading_level:
                                    can_merge = True

                        if can_merge:
                            nodes[-1].text += " " + text
                        elif heading_level:
                            nodes.append(
                                self.tree_svc.make_node(
                                    "heading", text=text, level=heading_level, page=page_num
                                )
                            )
                        else:
                            nodes.append(
                                self.tree_svc.make_node(
                                    "paragraph", text=text, page=page_num
                                )
                            )

                        # Reset so remaining words on this line merge normally
                        # into the newly created node.
                        has_double_newline = False

                    prev_line_bottom = line_bottom

                for table in page.extract_tables():
                    if table:
                        nodes.append(
                            self.tree_svc.make_node("table", page=page_num, content={"rows": table})
                        )

        return ParsedPDF(nodes=nodes, page_count=page_count)

    def _font_size_to_heading_level(self, size: float) -> int | None:
        for threshold, level in self.digital_pdf_heading_size_map:
            if size >= threshold:
                return level
        return None

    # –– Scanned PDFs –––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––––

    def parse_scanned_pdf(self, pdf_bytes: bytes) -> ParsedPDF:
        lang = get_settings().ocr_language
        images: list[Image.Image] = convert_from_bytes(pdf_bytes, dpi=self.ocr_dpi)
        page_count = len(images)
        nodes: list[DocumentContentTreeNode] = []

        for page_num, image in enumerate(images, start=1):
            data = pytesseract.image_to_data(
                image,
                lang=lang,
                output_type=pytesseract.Output.DICT,
            )

            # Tesseract groups words into blocks → paragraphs → lines.
            # A change in block_num or par_num is the OCR equivalent of a
            # double newline, so we use it to force a node break.
            # Words with the same classification merge into one node otherwise.
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

                has_paragraph_break = (
                    prev_block is not None
                    and (block_num != prev_block or par_num != prev_par)
                )

                heading_level = self._ocr_height_to_heading_level(height)
                node_type = "heading" if heading_level else "paragraph"

                can_merge = False
                if nodes and not has_paragraph_break:
                    last = nodes[-1]
                    if last.type == node_type and last.page == page_num:
                        if node_type == "paragraph":
                            can_merge = True
                        elif last.level == heading_level:
                            can_merge = True

                if can_merge:
                    nodes[-1].text += " " + text
                else:
                    nodes.append(self._classify_ocr_word(text, height, page_num))

                prev_block = block_num
                prev_par = par_num

        return ParsedPDF(nodes=nodes, page_count=page_count)

    def _ocr_height_to_heading_level(self, height: int) -> int | None:
        for threshold, level in self.ocr_heading_height_map:
            if height >= threshold:
                return level
        return None

    def _classify_ocr_word(
        self,
        text: str,
        height: int,
        page: int,
    ) -> DocumentContentTreeNode:
        level = self._ocr_height_to_heading_level(height)
        if level:
            return self.tree_svc.make_node("heading", text=text, level=level, page=page)
        return self.tree_svc.make_node("paragraph", text=text, page=page)

