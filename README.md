# SIH Local AI Workbench

A Windows desktop prototype for offline local-LLM chat, local PDF document analysis and local OCR for scanned PDFs.

The app uses Python, Tkinter, Ollama, a local `llama3.2:latest` model, PyMuPDF and Tesseract OCR. Users can attach a local PDF, extract text page by page, ask questions about the document and receive streamed answers from the local model.

## Current Status

Milestone 1 - Local interactive chat: complete.

Milestone 2 - Digital PDF document analysis: complete at prototype level.

Milestone 3 - Local OCR for scanned PDFs: complete at prototype level.

Implemented:

- Windows desktop UI built with Tkinter.
- Local Ollama chat using `llama3.2:latest`.
- Streaming responses while the model generates.
- Local PDF attachment through a file picker.
- PDF validation for file type, size, page count and readability.
- Native PDF text extraction with PyMuPDF.
- OCR fallback for scanned/image-only pages using local Tesseract through `pytesseract`.
- Mixed PDF support: native pages use native extraction, scanned pages use OCR.
- Page-aware document text using labels such as `[Page 1 | native]` and `[Page 2 | ocr]`.
- Three-page scanned PDF verification to confirm page order and page-specific facts survive OCR.
- Document Analysis mode and General Chat mode.
- Separate chat history for normal chat and document analysis.
- Document switching protection so a new PDF does not reuse old document context.
- Page-aware context budgeting instead of raw mid-page truncation.
- Clear handling for corrupted PDFs, blank image-only PDFs and unavailable OCR engine cases.
- Basic metrics in the UI: pages, extracted characters, extraction method, included context pages and LLM latency.
- Automated tests for PDF workflow, OCR workflow, app state and local model document QA.

Not implemented yet:

- Multi-document RAG.
- Vector database or embeddings.
- Source citation UI.
- Autonomous agents or tool execution.
- Docker/sandboxing.
- Fine-tuning or multiple model selection.

## Project Structure

```text
SIH_PROJECT_1/
  app.py
  requirements.txt
  run_chat_app.bat
  DOCUMENT_WORKFLOW_CHECKLIST.md
  README.md
  document/
    __init__.py
    extractor.py
    loader.py
    models.py
    ocr.py
  tests/
    create_synthetic_pdfs.py
    test_app_state.py
    test_demo_runs.py
    test_document_workflow.py
    test_model_document_qa.py
    data/
      synthetic_inspection_report.pdf
      synthetic_scanned_report.pdf
      synthetic_three_page_scanned_report.pdf
      synthetic_mixed_report.pdf
      synthetic_compressor_report.pdf
      synthetic_long_report.pdf
      synthetic_scanned_placeholder.pdf
      corrupted_input.pdf
```

## Requirements

- Windows
- Python 3.10 or newer
- Ollama installed locally
- Local Ollama model: `llama3.2:latest`
- Tesseract OCR installed locally

Install Ollama from:

```text
https://ollama.com
```

Pull the required model:

```powershell
ollama pull llama3.2
```

Install Tesseract OCR for Windows. The app checks:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
C:\Program Files (x86)\Tesseract-OCR\tesseract.exe
```

If Tesseract is on your `PATH`, that also works.

## Clone And Run From Git

Clone the repository:

```powershell
git clone https://github.com/harshit-033/SIH_PROJECT_1.git
cd SIH_PROJECT_1
```

Create a virtual environment:

```powershell
python -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Check Ollama and Tesseract:

```powershell
ollama list
.\.venv\Scripts\python.exe -c "from document.ocr import configure_tesseract; print(configure_tesseract())"
```

Start the app:

```powershell
python app.py
```

On Windows, you can also double-click:

```text
run_chat_app.bat
```

## How To Use

1. Open the app.
2. Use General Chat for normal local LLM questions.
3. Click `Attach PDF` to select a local PDF.
4. Digital pages are extracted with PyMuPDF.
5. Scanned pages are processed with local OCR.
6. Confirm the app switches to Document Analysis mode.
7. Ask questions about the selected document.
8. The answer streams into the chat window.
9. Click `Clear` to reset chat, document state, mode and metrics.

## Test Data

Synthetic test PDFs are included under `tests/data`.

Regenerate them with:

```powershell
.\.venv\Scripts\python.exe .\tests\create_synthetic_pdfs.py
```

Important test files:

- `synthetic_inspection_report.pdf`: digital PDF with known inspection facts.
- `synthetic_scanned_report.pdf`: scanned image PDF with known OCR facts.
- `synthetic_three_page_scanned_report.pdf`: scanned PDF with different facts on pages 1, 2 and 3.
- `synthetic_mixed_report.pdf`: one native page and one scanned page.
- `synthetic_long_report.pdf`: context-budgeting test.
- `synthetic_scanned_placeholder.pdf`: blank image-only PDF.
- `corrupted_input.pdf`: unreadable-PDF test.

## Verification

Run these commands from the project root:

```powershell
.\.venv\Scripts\python.exe -c "import pymupdf, pytesseract, PIL; print('document dependencies OK')"
.\.venv\Scripts\python.exe -c "from document.ocr import configure_tesseract; print(configure_tesseract())"
.\.venv\Scripts\python.exe -m py_compile .\app.py .\document\__init__.py .\document\models.py .\document\ocr.py .\document\extractor.py .\document\loader.py .\tests\create_synthetic_pdfs.py .\tests\test_document_workflow.py .\tests\test_app_state.py .\tests\test_demo_runs.py .\tests\test_model_document_qa.py
.\.venv\Scripts\python.exe .\tests\test_document_workflow.py
.\.venv\Scripts\python.exe .\tests\test_app_state.py
.\.venv\Scripts\python.exe .\tests\test_demo_runs.py
.\.venv\Scripts\python.exe .\tests\test_model_document_qa.py
```

`test_model_document_qa.py` calls the real local Ollama model, so Ollama must be running and `llama3.2:latest` must be installed.

## Security And Scope Notes

- PDF files are read from the local filesystem.
- OCR runs locally through Tesseract.
- The app does not upload documents or pages.
- The app does not use web search or cloud OCR.
- Prompts and document text are sent only to the local Ollama service.
- Document text is treated as untrusted reference material.
- This prototype should not be described as a complete air-gapped SIH system yet.

## Next Milestones

1. Add local chunking and embeddings.
2. Add a local vector store for multi-document RAG.
3. Add source citations and retrieval checks.
4. Add bounded tools or agent workflow only after document analysis is stable.
5. Add sandboxing, audit logs and network evidence for the final security story.
