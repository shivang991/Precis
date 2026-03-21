"""
Scanned PDF processor — converts scanned pages to images, runs Tesseract OCR,
then heuristically detects headings and builds Standard Format nodes.
"""

import io
import pytesseract
from PIL import Image
from pdf2image import convert_from_bytes
from app.services.standard_format import make_node
from app.services.pdf_processor import nest_nodes_by_heading
from app.config import get_settings

settings = get_settings()


def process_scanned_pdf(pdf_bytes: bytes) -> tuple[list[dict], int]:
    """
    OCR a scanned PDF and return Standard Format nodes + page count.

    Returns
    -------
    nodes      : nested Standard Format node dicts
    page_count : total page count
    """
    images: list[Image.Image] = convert_from_bytes(pdf_bytes, dpi=300)
    page_count = len(images)
    flat_nodes: list[dict] = []

    for page_num, image in enumerate(images, start=1):
        # Run Tesseract with layout analysis to get per-line bounding boxes + text
        data = pytesseract.image_to_data(
            image,
            lang=settings.ocr_language,
            output_type=pytesseract.Output.DICT,
        )

        n = len(data["text"])
        for i in range(n):
            text = data["text"][i].strip()
            conf = int(data["conf"][i])
            if not text or conf < 40:
                continue

            height = data["height"][i]
            node = _classify_ocr_line(text, height, page_num)
            flat_nodes.append(node)

    return nest_nodes_by_heading(flat_nodes), page_count


def _classify_ocr_line(text: str, height: int, page: int) -> dict:
    """
    Heuristic: taller text blocks are likely headings.
    These thresholds should be calibrated per document DPI.
    """
    if height >= 55:
        return make_node("heading", text=text, level=1, page=page)
    elif height >= 42:
        return make_node("heading", text=text, level=2, page=page)
    elif height >= 32:
        return make_node("heading", text=text, level=3, page=page)
    else:
        return make_node("paragraph", text=text, page=page)
