from __future__ import annotations

import logging
from pathlib import Path
from typing import Callable, Optional

from document.extractor import extract_page_text
from document.loader import (
    DIRECT_ANALYSIS_CHAR_BUDGET,
    MAX_PDF_PAGES,
    MAX_PDF_SIZE_MB,
    build_document_context,
    build_document_prompt,
    extract_pdf,
    validate_pdf_path,
)
from document.models import DocumentContext, DocumentExtraction, PageBlock
from document.ocr import configure_tesseract, find_tesseract_executable

logger = logging.getLogger(__name__)


class DocumentService:
    def __init__(self, char_budget: int = DIRECT_ANALYSIS_CHAR_BUDGET):
        self.char_budget = char_budget

    def check_ocr_availability(self) -> dict:
        exe = find_tesseract_executable()
        return {
            "tesseract_installed": bool(exe),
            "executable_path": exe or "",
        }

    def validate_file(self, file_path: str) -> None:
        validate_pdf_path(file_path)

    def process_pdf(
        self,
        file_path: str,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> DocumentExtraction:
        return extract_pdf(file_path, progress_callback=progress_callback)

    def create_context(self, pages: list[PageBlock]) -> DocumentContext:
        return build_document_context(pages, char_budget=self.char_budget)

    def format_prompt(self, user_question: str, context_text: str) -> str:
        return build_document_prompt(user_question, context_text)
