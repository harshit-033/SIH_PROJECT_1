from __future__ import annotations

import re
import shutil
from pathlib import Path

import pymupdf
import pytesseract
from PIL import Image


TESSERACT_CANDIDATES = [
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
]
OCR_DPI = 220
TESSERACT_CONFIG = "--psm 6"


class OCRUnavailableError(RuntimeError):
    pass


class OCRPageError(RuntimeError):
    pass


def find_tesseract_executable() -> str | None:
    path_from_env = shutil.which("tesseract")
    if path_from_env:
        return path_from_env

    for candidate in TESSERACT_CANDIDATES:
        if Path(candidate).exists():
            return candidate

    return None


def configure_tesseract() -> str:
    executable = find_tesseract_executable()
    if not executable:
        raise OCRUnavailableError(
            "Local OCR engine is unavailable. Install Tesseract OCR locally and try again."
        )

    pytesseract.pytesseract.tesseract_cmd = executable
    return executable


def normalize_ocr_text(text: str) -> str:
    lines = []
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = re.sub(r"[ \t]+", " ", raw_line).strip()
        line = line.replace("\ufffd", "")
        line = re.sub(r"(?<=\d)[O@](?=\d)", "", line)
        line = re.sub(r"[O@](?=\d)", "0", line)
        if line:
            lines.append(line)
    return "\n".join(lines)


def ocr_page(page: pymupdf.Page) -> str:
    configure_tesseract()

    try:
        pixmap = page.get_pixmap(dpi=OCR_DPI, alpha=False)
        image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
        text = pytesseract.image_to_string(image, lang="eng", config=TESSERACT_CONFIG)
    except OCRUnavailableError:
        raise
    except Exception as exc:
        raise OCRPageError("OCR failed for this page.") from exc

    return normalize_ocr_text(text)
