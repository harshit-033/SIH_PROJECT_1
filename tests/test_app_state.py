import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app import AppMode, LocalLLMChatApp, extract_pdf  # noqa: E402
from create_synthetic_pdfs import create_inspection_report  # noqa: E402


def check_composer_visibility(app: LocalLLMChatApp) -> None:
    app.geometry("900x620")
    app.update()

    if app.send_button.cget("text") != "Send":
        raise AssertionError("Send button label is missing")
    if app.prompt_input.winfo_height() < 60:
        raise AssertionError("Prompt textbox is too short to use")
    if app.send_button.winfo_width() < 80:
        raise AssertionError("Send button is too narrow")

    app.prompt_input.insert("1.0", "visibility check")
    app.update()
    if app.prompt_input.get("1.0", "end").strip() != "visibility check":
        raise AssertionError("Prompt textbox did not preserve typed text")
    if app.prompt_input.cget("fg") == app.prompt_input.cget("bg"):
        raise AssertionError("Prompt textbox text color matches background")


def main() -> None:
    app = LocalLLMChatApp()
    try:
        check_composer_visibility(app)
        extraction = extract_pdf(str(create_inspection_report()))
        app._handle_document_loaded(extraction)
        app.update_idletasks()

        if app.mode != AppMode.DOCUMENT_ANALYSIS:
            raise AssertionError("Expected Document Analysis mode after loading a PDF")
        if not app.current_document_context or not app.current_document_context.text:
            raise AssertionError("Expected a populated document context")
        if "PUMP-A17" not in app.current_document_context.text:
            raise AssertionError("Expected synthetic report facts in document context")

        app.clear_chat()
        app.update_idletasks()

        if app.mode != AppMode.GENERAL_CHAT:
            raise AssertionError("Expected General Chat mode after Clear")
        if app.current_document is not None or app.current_document_context is not None:
            raise AssertionError("Expected document state to be cleared")
    finally:
        app.destroy()

    print("Tkinter app state checks passed")


if __name__ == "__main__":
    main()
