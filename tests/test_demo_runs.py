import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app import AppMode, LocalLLMChatApp, extract_pdf  # noqa: E402
from create_synthetic_pdfs import (  # noqa: E402
    create_inspection_report,
    create_mixed_report,
    create_scanned_inspection_report,
)


def load_and_verify(app: LocalLLMChatApp, pdf_path: Path, expected_text: str, expected_method: str) -> None:
    extraction = extract_pdf(str(pdf_path))
    app._handle_document_loaded(extraction)
    app.update()

    if app.mode != AppMode.DOCUMENT_ANALYSIS:
        raise AssertionError(f"Expected Document Analysis mode for {pdf_path.name}")
    if not app.current_document_context or expected_text not in app.current_document_context.text:
        raise AssertionError(f"Expected {expected_text} in active context for {pdf_path.name}")
    if expected_method not in app.method_metric.cget("text"):
        raise AssertionError(f"Expected method metric to include {expected_method}")


def run_demo_once(run_number: int) -> None:
    app = LocalLLMChatApp()
    try:
        app.update()
        if app.mode != AppMode.GENERAL_CHAT:
            raise AssertionError(f"Run {run_number}: app did not start in General Chat")

        load_and_verify(app, create_inspection_report(), "PUMP-A17", "native")
        load_and_verify(app, create_scanned_inspection_report(), "SCAN-A01", "OCR")
        load_and_verify(app, create_mixed_report(), "MIX-SCAN-02", "mixed")

        app.clear_chat()
        app.update()
        if app.mode != AppMode.GENERAL_CHAT:
            raise AssertionError(f"Run {run_number}: Clear did not restore General Chat")
        if app.current_document is not None or app.current_document_context is not None:
            raise AssertionError(f"Run {run_number}: Clear did not reset document state")
    finally:
        app.destroy()


def main() -> None:
    for run_number in range(1, 4):
        run_demo_once(run_number)
        print(f"Demo-equivalent run {run_number}: PASS")

    print("Three complete demo-equivalent runs passed")


if __name__ == "__main__":
    main()
