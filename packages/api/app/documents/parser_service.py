import io
from dataclasses import dataclass

import pdfplumber
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes

from app.document_content_tree.schemas import StandardFormatNode
from app.document_content_tree.service import DocumentContentTreeService
from app.shared.config import get_settings


@dataclass(frozen=True)
class ParsedPDF:
    nodes: list[StandardFormatNode]
    page_count: int


class ParserService:

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
        nodes: list[StandardFormatNode] = []

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

                    avg_size = sum(w.get("size", 10) for w in line_words) / len(
                        line_words
                    )
                    heading_level = self._font_size_to_heading_level(avg_size)

                    if heading_level:
                        nodes.append(
                            DocumentContentTreeService.make_node(
                                "heading", text=text, level=heading_level, page=page_num
                            )
                        )
                    else:
                        nodes.append(DocumentContentTreeService.make_node("paragraph", text=text, page=page_num))

                for table in page.extract_tables():
                    if table:
                        nodes.append(
                            DocumentContentTreeService.make_node("table", page=page_num, content={"rows": table})
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
        flat_nodes: list[StandardFormatNode] = []

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
                if not text or conf < self.ocr_min_confidence:
                    continue

                height = data["height"][i]
                flat_nodes.append(self._classify_ocr_line(text, height, page_num))

        return ParsedPDF(nodes=flat_nodes, page_count=page_count)

    def _classify_ocr_line(
        self,
        text: str,
        height: int,
        page: int,
    ) -> StandardFormatNode:
        for threshold, level in self.ocr_heading_height_map:
            if height >= threshold:
                return DocumentContentTreeService.make_node("heading", text=text, level=level, page=page)
        return DocumentContentTreeService.make_node("paragraph", text=text, page=page)

