# SIH Local AI Workbench

A fully offline, multi-client local AI system for LLM chat, digital PDF document analysis, and OCR for scanned documents over a Local Area Network (LAN).

The host machine runs Ollama (`llama3.2:latest`), Tesseract OCR, and a FastAPI server. Multiple client laptops on the same network can connect simultaneously via a web browser to analyze documents, chat with the AI, and manage users without needing GPUs or local AI installations on client machines.

---

## Features

- **Multi-Client Local AI Server**: FastAPI server with Server-Sent Events (SSE) token streaming over LAN.
- **Web Interface**: Dark-mode web interface accessible from any browser (`http://<SERVER-IP>:8000`).
- **Role-Based Access Control (RBAC)**:
  - **Admin**: Full access to AI workspace, user management dashboard, and profile self-management.
  - **User**: Access to AI chat and document analysis workspace.
- **Admin Profile Management**:
  - Admin can update their username (with uniqueness enforcement).
  - Admin can update their password (requires old password verification).
- **Single Active Admin Session**:
  - Strict server-side invariant allowing at most one active admin session at a time.
  - Rejects secondary admin logins with `409 Conflict` until the active session logs out or expires.
  - Normal users can log in across multiple clients concurrently.
- **Session & Data Isolation**:
  - Each client session has isolated chat histories, uploaded documents, and file contexts.
- **Hybrid PDF Extraction**:
  - Fast native text extraction via PyMuPDF.
  - Automatic fallback to local Tesseract OCR for scanned/image pages.
- **Desktop Tkinter Client**:
  - Offline standalone desktop application (`app.py`) also included.

---

## Prerequisites

- **OS**: Windows 10/11
- **Python**: 3.10 or newer
- **Ollama**: Installed locally with `llama3.2:latest` model (`ollama pull llama3.2`)
- **Tesseract OCR**: Installed locally (e.g., in `C:\Program Files\Tesseract-OCR`)

---

## Quick Start

### 1. Clone the Repository
```powershell
git clone https://github.com/harshit-033/SIH_PROJECT_1.git
cd SIH_PROJECT_1
```

### 2. Set Up Virtual Environment & Dependencies
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

### 3. Start the Server (Web UI + Multi-Client LAN Access)
```powershell
.\.venv\Scripts\python.exe run_server.py
```
*(Or double-click `run_server.bat`)*

- **Local URL**: `http://localhost:8000`
- **Network URL**: `http://<SERVER-LAN-IP>:8000`
- **API Docs**: `http://localhost:8000/docs`

### 4. (Optional) Run the Standalone Desktop GUI
```powershell
.\.venv\Scripts\python.exe app.py
```
*(Or double-click `run_chat_app.bat`)*

---

## Default Accounts

| Username | Password | Role | Description |
| :--- | :--- | :--- | :--- |
| `admin` | `admin123` | `admin` | Admin panel, user management, My Account profile, AI workspace |
| `user1` | `pass123` | `user` | AI chat & document analysis workspace |
| `user2` | `pass123` | `user` | AI chat & document analysis workspace |
| `inspector` | `sih2026` | `user` | AI chat & document analysis workspace |

*Passwords are securely hashed using salted PBKDF2-HMAC-SHA256.*

---

## Project Structure

```text
SIH_PROJECT_1/
├── core/                   # Server backend core modules
│   ├── ai_service.py       # Ollama LLM integration and health checks
│   ├── auth.py             # Authentication & session token management
│   ├── document_service.py # PDF extraction and context budgeting
│   ├── file_handler.py     # Upload sanitization and session cleanup
│   ├── models.py           # Dataclasses and enums
│   ├── monitoring.py       # CPU, RAM, and queue telemetry
│   ├── request_queue.py    # Request serialization queue
│   ├── session_manager.py  # In-memory session tracking
│   └── user_store.py       # Persistent JSON user storage
├── data/
│   └── users.json          # Persistent user database
├── document/               # Standalone document processing engine
│   ├── extractor.py        # PDF text & OCR router
│   ├── loader.py           # PyMuPDF loader
│   ├── models.py           # PageBlock, DocumentExtraction models
│   └── ocr.py              # Tesseract OCR engine wrapper
├── server/
│   └── main.py             # FastAPI server application & routes
├── static/                 # Web UI assets
│   ├── app.css             # Stylesheet
│   ├── app.js              # Frontend client application logic
│   └── index.html          # Web UI interface
├── tests/                  # Automated test suites
│   ├── test_admin_profile.py
│   ├── test_api_server.py
│   ├── test_app_state.py
│   ├── test_concurrency_queue.py
│   ├── test_demo_runs.py
│   ├── test_document_workflow.py
│   ├── test_lan_server_e2e.py
│   ├── test_model_document_qa.py
│   ├── test_rbac_auth.py
│   ├── test_security_file_handling.py
│   └── test_session_isolation.py
├── app.py                  # Tkinter desktop GUI client
├── run_server.py           # Server entrypoint with LAN IP detection
├── run_server.bat          # Windows launcher for server
├── run_chat_app.bat        # Windows launcher for desktop app
├── requirements.txt        # Python package dependencies
├── SERVER_GUIDE.md         # Detailed server and RBAC reference
└── README.md               # Project documentation
```

---

## Running Tests

To run the complete automated test suite:

```powershell
# RBAC and User Management tests
.\.venv\Scripts\python.exe .\tests\test_rbac_auth.py

# Admin Profile & Single Active Admin Session tests
.\.venv\Scripts\python.exe .\tests\test_admin_profile.py

# Multi-Client Isolation & E2E tests
.\.venv\Scripts\python.exe .\tests\test_session_isolation.py
.\.venv\Scripts\python.exe .\tests\test_lan_server_e2e.py

# API Server & Security tests
.\.venv\Scripts\python.exe .\tests\test_api_server.py
.\.venv\Scripts\python.exe .\tests\test_security_file_handling.py

# Document Processing & Concurrency tests
.\.venv\Scripts\python.exe .\tests\test_document_workflow.py
.\.venv\Scripts\python.exe .\tests\test_concurrency_queue.py
```
