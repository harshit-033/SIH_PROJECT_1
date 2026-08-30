# SIH Local AI Workbench

A Windows desktop prototype for offline local-LLM chat and local PDF document analysis.

The app uses Python, Tkinter, Ollama and a local `llama3.2:latest` model. It is designed for the SIH workflow where a user selects a local PDF, extracts text locally, asks questions about the document and receives streamed answers from the local model.

## Current Status

Milestone 1 - Local interactive chat: complete.

Milestone 2 - Local PDF document analysis: complete at prototype level.

Implemented:

- Windows desktop UI built with Tkinter.
- Local Ollama chat using `llama3.2:latest`.
- Streaming responses, so answers appear while the model generates.
- Local PDF attachment through a file picker.
- PDF validation for file type, size, page count and readability.
- PDF text extraction with PyMuPDF.
- Page-aware document text using labels such as `[Page 1]`.
- Document Analysis mode and General Chat mode.
- Separate chat history for normal chat and document analysis.
- Document switching protection so a new PDF does not reuse old document context.
- Page-aware context budgeting instead of raw mid-page truncation.
- Friendly handling for scanned/image-only PDFs that need OCR.
- Basic metrics in the UI: pages, extracted characters, included context pages and LLM latency.
- Automated tests for PDF workflow, app state and local model document QA.

Not implemented yet:

- OCR for scanned PDFs.
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
  tests/
    create_synthetic_pdfs.py
    test_app_state.py
    test_document_workflow.py
    test_model_document_qa.py
    data/
      synthetic_inspection_report.pdf
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

Install Ollama from:

```text
https://ollama.com
```

Pull the required model:

```powershell
ollama pull llama3.2
```

Check that the model is available:

```powershell
ollama list
```

You should see `llama3.2:latest`.

## Clone And Run From Git

Clone the repository:

```powershell
git clone <your-repository-url>
cd <your-repository-folder>
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

Start Ollama if it is not already running, then launch the app:

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
3. Click `Attach PDF` to select a local digital PDF.
4. Confirm the app switches to Document Analysis mode.
5. Ask questions about the selected document.
6. The answer streams into the chat window.
7. Click `Clear` to reset chat, document state, mode and metrics.

## Test Data

Synthetic test PDFs are included under `tests/data`.

Regenerate them with:

```powershell
.\.venv\Scripts\python.exe .\tests\create_synthetic_pdfs.py
```

The main synthetic inspection report includes fixed facts such as:

- Equipment ID: `PUMP-A17`
- Bearing temperature: `86 C`
- Vibration: `7.8 mm/s`
- Main findings: elevated bearing temperature and increased vibration trend

## Verification

Run these commands from the project root:

```powershell
.\.venv\Scripts\python.exe -c "import pymupdf; print('PyMuPDF OK')"
.\.venv\Scripts\python.exe -m py_compile .\app.py .\tests\create_synthetic_pdfs.py .\tests\test_document_workflow.py .\tests\test_app_state.py .\tests\test_model_document_qa.py
.\.venv\Scripts\python.exe .\tests\test_document_workflow.py
.\.venv\Scripts\python.exe .\tests\test_app_state.py
.\.venv\Scripts\python.exe .\tests\test_model_document_qa.py
```

`test_model_document_qa.py` calls the real local Ollama model, so Ollama must be running and `llama3.2:latest` must be installed.

## Manual Demo Checklist

1. Launch the app.
2. Ask a normal question without a PDF and confirm the response streams.
3. Attach `tests\data\synthetic_inspection_report.pdf`.
4. Ask `What is the equipment ID?` and confirm the answer contains `PUMP-A17`.
5. Ask `What was the bearing temperature?` and confirm the answer contains `86 C`.
6. Ask `What are the main findings?` and confirm it mentions bearing temperature and vibration trend.
7. Ask `What is the warranty expiration date?` and confirm it says the information is not available in the document.
8. Attach `tests\data\synthetic_compressor_report.pdf`.
9. Ask for the equipment ID and confirm it answers `COMP-B44`, not `PUMP-A17`.
10. Attach `tests\data\synthetic_scanned_placeholder.pdf` and confirm the app says OCR is required.
11. Click `Clear` and confirm the app returns to General Chat.

## Security And Scope Notes

- PDF files are read from the local filesystem.
- The app does not upload documents.
- The app does not use web search or cloud OCR.
- Prompts and document text are sent only to the local Ollama service.
- Document text is treated as untrusted reference material.
- This prototype should not be described as a complete air-gapped SIH system yet.

## Next Milestones

1. Add local OCR for scanned PDFs.
2. Add local embeddings and multi-document RAG.
3. Add source citations and retrieval checks.
4. Add bounded tools or agent workflow only after document analysis is stable.
5. Add sandboxing, audit logs and network evidence for the final security story.
