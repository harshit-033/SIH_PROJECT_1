from __future__ import annotations

import re

import pymupdf

from .models import PageBlock
from .ocr import OCRPageError, OCRUnavailableError, ocr_page


MIN_USABLE_TEXT_CHARS = 30
MIN_USABLE_ALNUM_CHARS = 12


def normalize_native_text(text: str) -> str:
    lines = []
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def is_usable_text(text: str) -> bool:
    cleaned = text.strip()
    alnum_count = sum(character.isalnum() for character in cleaned)
    return len(cleaned) >= MIN_USABLE_TEXT_CHARS and alnum_count >= MIN_USABLE_ALNUM_CHARS


def extract_page_text(
    page: pymupdf.Page,
    page_number: int,
    source: str,
    page_count: int,
    progress_callback=None,
) -> tuple[PageBlock | None, bool, bool]:
    native_text = normalize_native_text(page.get_text("text"))
    if is_usable_text(native_text):
        return PageBlock(page_number, native_text, "native", source), False, False

    if progress_callback:
        progress_callback(f"OCR processing page {page_number}/{page_count}...")

    try:
        text = ocr_page(page)
    except OCRUnavailableError:
        raise
    except OCRPageError:
        return None, True, True

    if is_usable_text(text):
        return PageBlock(page_number, text, "ocr", source), True, False

    return None, True, True
