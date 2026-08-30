# SIH Milestone 2 - Local PDF Document Analysis

## Implemented

- Tkinter app starts from the project virtual environment through `run_chat_app.bat`.
- Ollama remains the only model endpoint.
- Model name is centralized in `MODEL_NAME`.
- App modes are explicit: `GENERAL_CHAT` and `DOCUMENT_ANALYSIS`.
- PDF attachment uses a local file picker that accepts PDF files.
- PDF validation checks existence, file extension, file size and page count.
- Current limits are 25 MB, 80 pages and 14,000 direct-analysis characters.
- Selected PDF filename and active mode are visible in the UI.
- PDF text extraction uses PyMuPDF from the local filesystem.
- Extracted text is stored as complete page blocks.
- Page labels such as `[Page 1]` are preserved for future citations.
- Direct document context is built page-by-page and never slices a page in the middle.
- The UI warns when only part of a long document fits the current direct-analysis limit.
- Empty or image-only PDFs are handled as an OCR-needed case without crashing.
- Corrupted or unreadable PDFs fail with a friendly message.
- Document session history resets when a new PDF is attached.
- General chat history and document-analysis history are kept separate.
- Full document text is not permanently appended to chat history.
- Document prompt treats PDF text as untrusted reference material.
- Streaming queue/thread architecture remains intact.
- Basic measurements are shown: page count, extracted characters, context pages and LLM latency.
- The input composer is reserved in the layout so resizing the window does not hide the textbox.
- The prompt textbox uses explicit readable foreground/background colors.
- The Send button uses a standard Tkinter button with a visible text label.
- Clear resets chat history, document state, mode and measurements.
- Synthetic PDF tests are available in `tests\data`.

## Test Data

- `tests\data\synthetic_inspection_report.pdf`
- `tests\data\synthetic_compressor_report.pdf`
- `tests\data\synthetic_long_report.pdf`
- `tests\data\synthetic_scanned_placeholder.pdf`
- `tests\data\corrupted_input.pdf`

Regenerate them with:

```powershell
.\.venv\Scripts\python.exe .\tests\create_synthetic_pdfs.py
```

## Verification Commands

Run these from the project folder:

```powershell
.\.venv\Scripts\python.exe -c "import pymupdf; print('PyMuPDF OK')"
.\.venv\Scripts\python.exe -m py_compile .\app.py .\tests\create_synthetic_pdfs.py .\tests\test_document_workflow.py .\tests\test_model_document_qa.py
.\.venv\Scripts\python.exe .\tests\test_document_workflow.py
.\.venv\Scripts\python.exe .\tests\test_app_state.py
.\.venv\Scripts\python.exe .\tests\test_model_document_qa.py
```

## Manual Demo Flow

1. Double-click `run_chat_app.bat`.
2. Confirm the app opens as `SIH Local AI Workbench`.
3. Without a document, ask a normal question and confirm the answer streams.
4. Click `Attach PDF`.
5. Select `tests\data\synthetic_inspection_report.pdf`.
6. Confirm `Document Analysis` mode, filename, page count, extracted characters and context pages appear.
7. Ask `What is the equipment ID?` and confirm the answer contains `PUMP-A17`.
8. Ask `What was the bearing temperature?` and confirm the answer contains `86 C`.
9. Ask `What are the main findings?` and confirm it mentions bearing temperature and vibration trend.
10. Ask `What is the warranty expiration date?` and confirm it says the information is not available in the document.
11. Attach `tests\data\synthetic_compressor_report.pdf` and confirm the mode switches to that document.
12. Ask for the equipment ID and confirm the answer is `COMP-B44`, not `PUMP-A17`.
13. Attach `tests\data\synthetic_long_report.pdf` and confirm the context-limit warning appears.
14. Attach `tests\data\synthetic_scanned_placeholder.pdf` and confirm the app says OCR is required.
15. Try `tests\data\corrupted_input.pdf` and confirm a clean unreadable-PDF error.
16. Click `Clear` and confirm the app returns to `General Chat` with no selected document.
17. Repeat the demo three times before moving to OCR.

## Current Scope Boundary

This milestone intentionally does not add RAG, OCR, agents, Docker, multiple models, fine-tuning, telemetry, remote upload, or web retrieval.
