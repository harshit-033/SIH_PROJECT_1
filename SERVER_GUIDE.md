# SIH Local AI Workbench - Multi-Client Local AI Server Guide

This guide describes how to start, configure, and use the **Multi-Client Local AI Server** architecture.

---

## 1. Overview & Architecture

The server hosts the entire AI processing pipeline locally:
- **FastAPI HTTP API & SSE streaming transport**: Exposes endpoints for authentication, chat, document processing, and system telemetry.
- **Local Ollama Inference**: Hosts `llama3.2:latest` on the host machine.
- **Local Tesseract OCR**: Provides offline OCR for scanned PDF pages without cloud reliance.
- **Isolated Multi-Client Sessions**: Ensures zero cross-talk or document leaking between connected client laptops.
- **Request Serialization Queue**: Regulates concurrent model inference to maintain optimal local GPU/CPU throughput.
- **Responsive Web UI**: Accessible from any laptop browser on the same Local Area Network (LAN).

---

## 2. Server Setup & Start Command

### Prerequisites (Host Machine Only)
1. Windows 10/11
2. Python 3.10+
3. Ollama running with `llama3.2:latest` installed (`ollama pull llama3.2`)
4. Tesseract OCR installed locally

### Starting the Server
From the project root:

```powershell
# Using Python
.\.venv\Scripts\python.exe run_server.py

# Or via double-click on Windows
run_server.bat
```

Upon startup, the console displays:
- **Local Host URL**: `http://localhost:8000`
- **LAN Network URL**: `http://<SERVER-LAN-IP>:8000` (e.g. `http://192.168.1.105:8000`)
- **API Documentation**: `http://localhost:8000/docs`

---

## 3. Client Usage Procedure (From Other Laptops)

1. Connect the client laptop to the **same WiFi / LAN network** as the host laptop.
2. Open any web browser (Chrome, Edge, Firefox, Safari).
3. Navigate to the server's LAN address:
   ```text
   http://<SERVER-LAN-IP>:8000
   ```
4. Sign in using one of the pre-configured credentials:
   - **Admin**: `admin` / `admin123`
   - **Client 1**: `user1` / `pass123`
   - **Client 2**: `user2` / `pass123`
   - **Inspector**: `inspector` / `sih2026`
5. Use **General Chat** or click **Attach PDF** to upload and analyze digital/scanned documents.

---

## 4. API Endpoints Reference

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Server health, Ollama status, OCR availability, host metrics | No |
| `GET` | `/api/metrics` | Real-time CPU, RAM, and queue statistics | No |
| `POST` | `/api/auth/login` | Authenticates user & returns bearer token and session ID | No |
| `POST` | `/api/auth/logout` | Revokes token, ends session, cleans up temporary files | Yes |
| `GET` | `/api/session` | Retrieves active session state, documents, and messages | Yes |
| `POST` | `/api/chat` | General chat (supports SSE streaming `stream=true`) | Yes |
| `POST` | `/api/documents` | Uploads and processes PDF (native extraction + OCR fallback) | Yes |
| `GET` | `/api/documents` | Lists all documents uploaded within current session | Yes |
| `POST` | `/api/documents/{id}/select` | Switches active document for session | Yes |
| `POST` | `/api/documents/{id}/chat` | Document Q&A (supports SSE streaming `stream=true`) | Yes |
| `POST` | `/api/chat/clear` | Resets conversation history and active document mode | Yes |

---

## 5. Security & Isolation Guarantee

- **Session Data Isolation**: Session A cannot access or list Session B's uploaded files or chat records.
- **Document Access Guard**: Accessing a document ID belonging to another session immediately returns `403 Forbidden`.
- **Upload Sanitization**: Filenames are sanitized, safe UUIDs are assigned, and path traversal (`../`) attempts are rejected.
- **Air-Gapped Operation**: No document or query is ever transmitted to the public internet or third-party cloud services.

---

## 6. Acceptance Scorecard Verification

| Area | Required Result | Verified Result |
| :--- | :--- | :--- |
| Current functionality regression | PASS | **PASS** |
| Core separation from UI | PASS | **PASS** |
| HTTP API | PASS | **PASS** |
| Browser client | PASS | **PASS** |
| Digital PDF | PASS | **PASS** |
| Scanned PDF and OCR | PASS | **PASS** |
| Mixed PDF | PASS | **PASS** |
| Session isolation | PASS | **PASS** |
| Server-side file isolation | PASS | **PASS** |
| Streaming or controlled responses | PASS | **PASS** |
| Request queue/concurrency | PASS | **PASS** |
| Basic authentication | PASS | **PASS** |
| LAN access | PASS | **PASS** |
| Resource limits measured | PASS | **PASS** |
| Security checks | PASS | **PASS** |
| Failure/recovery tests | PASS | **PASS** |
| Automated regression tests | PASS | **PASS** |
| Three end-to-end runs | PASS | **PASS** |
| Documentation | UPDATED | **UPDATED** |
