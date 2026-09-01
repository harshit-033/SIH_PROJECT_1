from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class PageBlock:
    page_number: int
    text: str
    method: str
    source: str

    def as_prompt_text(self) -> str:
        return f"[Page {self.page_number} | {self.method}]\n{self.text}"


@dataclass(frozen=True)
class DocumentExtraction:
    path: str
    page_count: int
    pages: list[PageBlock]
    extracted_chars: int
    extraction_seconds: float
    file_size_mb: float
    native_pages: int = 0
    ocr_pages: int = 0
    ocr_attempted_pages: int = 0
    failed_pages: list[int] = field(default_factory=list)

    @property
    def filename(self) -> str:
        return Path(self.path).name

    @property
    def method_summary(self) -> str:
        if self.native_pages and self.ocr_pages:
            return f"mixed: {self.native_pages} native, {self.ocr_pages} OCR"
        if self.ocr_pages:
            return f"OCR: {self.ocr_pages} pages"
        if self.native_pages:
            return f"native: {self.native_pages} pages"
        if self.ocr_attempted_pages:
            return "OCR attempted, no readable text"
        return "no readable text"


@dataclass(frozen=True)
class DocumentContext:
    text: str
    included_pages: int
    total_text_pages: int
    truncated: bool
    estimated_tokens: int
