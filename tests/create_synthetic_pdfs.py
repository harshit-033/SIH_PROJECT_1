from io import BytesIO
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw, ImageFont


TEST_DATA_DIR = Path(__file__).resolve().parent / "data"


def save_pdf(doc: pymupdf.Document, output_path: Path) -> None:
    temp_path = output_path.with_suffix(".tmp.pdf")
    if temp_path.exists():
        temp_path.unlink()
    doc.save(temp_path)
    doc.close()
    try:
        temp_path.replace(output_path)
    except PermissionError:
        if output_path.exists():
            temp_path.unlink(missing_ok=True)
            return
        raise


def add_text_page(doc: pymupdf.Document, lines: list[str]) -> None:
    page = doc.new_page()
    y = 72
    for line in lines:
        page.insert_text((72, y), line, fontsize=11)
        y += 18


def create_text_image(lines: list[str]) -> bytes:
    image = Image.new("RGB", (1400, 1800), "white")
    draw = ImageDraw.Draw(image)
    try:
        title_font = ImageFont.truetype("calibri.ttf", 52)
        body_font = ImageFont.truetype("calibri.ttf", 44)
    except OSError:
        try:
            title_font = ImageFont.truetype("segoeui.ttf", 52)
            body_font = ImageFont.truetype("segoeui.ttf", 44)
        except OSError:
            title_font = ImageFont.load_default()
            body_font = ImageFont.load_default()

    y = 130
    for index, line in enumerate(lines):
        font = title_font if index == 0 else body_font
        draw.text((110, y), line, fill="black", font=font)
        y += 78

    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=95, optimize=True)
    return buffer.getvalue()


def add_scanned_page(doc: pymupdf.Document, lines: list[str]) -> None:
    page = doc.new_page(width=595, height=842)
    image_bytes = create_text_image(lines)
    page.insert_image(page.rect, stream=image_bytes)


def create_inspection_report() -> Path:
    TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_path = TEST_DATA_DIR / "synthetic_inspection_report.pdf"

    doc = pymupdf.open()
    add_text_page(
        doc,
        [
            "Synthetic Industrial Inspection Report",
            "Equipment ID: PUMP-A17",
            "Inspection date: 2026-08-30",
            "Inspector: Test Engineer",
            "Measured vibration: 7.8 mm/s",
            "Measured bearing temperature: 86 C",
            "Observation: Coupling guard is intact.",
        ],
    )
    add_text_page(
        doc,
        [
            "Findings and Recommendations",
            "Main findings:",
            "1. Bearing temperature exceeded the normal threshold.",
            "2. Vibration trend increased over the last two checks.",
            "Recommendation: Schedule bearing inspection within 7 days.",
            "Recommendation: Re-check shaft alignment during the next shutdown.",
        ],
    )
    save_pdf(doc, output_path)
    return output_path


def create_scanned_inspection_report() -> Path:
    TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_path = TEST_DATA_DIR / "synthetic_scanned_report.pdf"

    doc = pymupdf.open()
    add_scanned_page(
        doc,
        [
            "Synthetic Scanned Inspection Report",
            "Equipment ID: SCAN-A01",
            "Inspection date: 2026-09-01",
            "Bearing temperature: 82 C",
            "Vibration: 6.4 mm/s",
            "Finding: Bearing temperature is slightly elevated.",
            "Recommendation: Inspect lubrication system.",
        ],
    )
    save_pdf(doc, output_path)
    return output_path


def create_three_page_scanned_report() -> Path:
    TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_path = TEST_DATA_DIR / "synthetic_three_page_scanned_report.pdf"

    doc = pymupdf.open()
    add_scanned_page(
        doc,
        [
            "Three Page OCR Report",
            "Page 1 unique fact: ALPHA-101",
            "Equipment ID: SCAN-PAGE-01",
            "Measured flow: 120 LPM",
        ],
    )
    add_scanned_page(
        doc,
        [
            "Three Page OCR Report",
            "Page 2 unique fact: BRAVO-202",
            "Bearing temperature: 82 C",
            "Measured vibration: 6.4 mm/s",
        ],
    )
    add_scanned_page(
        doc,
        [
            "Three Page OCR Report",
            "Page 3 unique fact: CHARLIE-303",
            "Recommendation: Inspect lubrication system.",
            "Review priority: HIGH",
        ],
    )
    save_pdf(doc, output_path)
    return output_path


def create_mixed_report() -> Path:
    TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_path = TEST_DATA_DIR / "synthetic_mixed_report.pdf"

    doc = pymupdf.open()
    add_text_page(
        doc,
        [
            "Synthetic Mixed Report",
            "Native page equipment ID: MIX-NATIVE-01",
            "Native page status: pump casing is stable.",
        ],
    )
    add_scanned_page(
        doc,
        [
            "Scanned Follow-up Page",
            "Scanned page equipment ID: MIX-SCAN-02",
            "Scanned finding: seal leakage requires review.",
        ],
    )
    save_pdf(doc, output_path)
    return output_path


def create_compressor_report() -> Path:
    TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_path = TEST_DATA_DIR / "synthetic_compressor_report.pdf"

    doc = pymupdf.open()
    add_text_page(
        doc,
        [
            "Synthetic Compressor Maintenance Report",
            "Equipment ID: COMP-B44",
            "Inspection date: 2026-08-31",
            "Measured discharge pressure: 11.2 bar",
            "Measured oil temperature: 72 C",
            "Main finding: Intake filter loading is above the preferred range.",
        ],
    )
    save_pdf(doc, output_path)
    return output_path


def create_long_report(page_count: int = 12) -> Path:
    TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_path = TEST_DATA_DIR / "synthetic_long_report.pdf"

    doc = pymupdf.open()
    repeated_line = (
        "Routine measurement block: pressure stable, vibration nominal, "
        "temperature within expected range for this synthetic test document."
    )
    for page_no in range(1, page_count + 1):
        lines = [f"Synthetic Long Report - Page {page_no}"]
        lines.extend(f"{repeated_line} Row {row}." for row in range(1, 38))
        add_text_page(doc, lines)

    save_pdf(doc, output_path)
    return output_path


def create_image_only_placeholder() -> Path:
    TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_path = TEST_DATA_DIR / "synthetic_scanned_placeholder.pdf"

    doc = pymupdf.open()
    page = doc.new_page()
    shape = page.new_shape()
    shape.draw_rect(pymupdf.Rect(72, 72, 520, 300))
    shape.finish(color=(0.2, 0.2, 0.2), fill=(0.92, 0.92, 0.92))
    shape.commit()
    save_pdf(doc, output_path)
    return output_path


def create_corrupted_pdf() -> Path:
    TEST_DATA_DIR.mkdir(parents=True, exist_ok=True)
    output_path = TEST_DATA_DIR / "corrupted_input.pdf"
    output_path.write_text("This is not a valid PDF file.", encoding="utf-8")
    return output_path


def main() -> None:
    print(create_inspection_report())
    print(create_scanned_inspection_report())
    print(create_three_page_scanned_report())
    print(create_mixed_report())
    print(create_compressor_report())
    print(create_long_report())
    print(create_image_only_placeholder())
    print(create_corrupted_pdf())


if __name__ == "__main__":
    main()
