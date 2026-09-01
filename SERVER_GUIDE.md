# SIH Local AI Workbench - Multi-Client Local AI Server Guide

This guide describes how to start, configure, and use the **Multi-Client Local AI Server** architecture with **Role-Based Access Control (RBAC)** and **User Management**.

---

## 1. Overview & Architecture

The server hosts the entire AI processing pipeline locally:
- **FastAPI HTTP API & SSE streaming transport**: Exposes endpoints for authentication, RBAC, chat, document processing, and system telemetry.
- **Role-Based Access Control (RBAC)**: Exactly two roles (`admin` and `user`). Admins can manage users and use AI workspace. Normal users can use AI workspace only.
- **Local Ollama Inference**: Hosts `llama3.2:latest` on the host machine.
- **Local Tesseract OCR**: Provides offline OCR for scanned PDF pages without cloud reliance.
- **Persistent User Storage**: Local JSON storage (`data/users.json`) with salted PBKDF2-HMAC-SHA256 password hashing.
- **Isolated Multi-Client Sessions**: Ensures zero cross-talk or document leaking between connected client laptops.
- **Request Serialization Queue**: Regulates concurrent model inference to maintain optimal local GPU/CPU throughput.
- **Responsive Web UI**: Accessible from any laptop browser on the same Local Area Network (LAN) with dynamic role-based interface views.

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
4. Sign in using your credentials:
   - **Admin Account**: `admin` / `admin123` (Access to AI workspace + Admin Dashboard)
   - **User Accounts**: `user1` / `pass123`, `user2` / `pass123`, `inspector` / `sih2026` (AI workspace only)
5. **If Admin**: Click **Admin Dashboard** in the top navigation bar to view, create, or remove users.
6. Use **General Chat** or click **Attach PDF** to upload and analyze digital/scanned documents.

---

## 4. Capability Matrix & RBAC

| Capability | Admin Role | User Role | Unauthenticated |
| :--- | :--- | :--- | :--- |
| **Login** | YES | YES | NO |
| **Use AI Workspace (Chat & Documents)** | YES | YES | NO (401) |
| **Admin Dashboard UI** | YES | NO (Hidden) | NO |
| **Create Users (`POST /api/admin/users`)** | YES | NO (403) | NO (401) |
| **View Users (`GET /api/admin/users`)** | YES | NO (403) | NO (401) |
| **Remove / Deactivate User (`DELETE /api/admin/users/{id}`)** | YES | NO (403) | NO (401) |
| **Remove Self / Last Admin** | NO (400) | NO | NO |
| **Access Another User's Data / Docs** | NO (403) | NO (403) | NO (401) |
| **Public Self-Registration** | NO (Disabled) | NO (Disabled) | NO (Disabled) |

---

## 5. API Endpoints Reference

| Method | Endpoint | Description | Access Level |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Server health, Ollama status, OCR availability, host metrics | Public |
| `GET` | `/api/metrics` | Real-time CPU, RAM, and queue statistics | Public |
| `POST` | `/api/auth/login` | Authenticates user & returns bearer token and session ID | Public |
| `POST` | `/api/auth/logout` | Revokes token, ends session, cleans up temporary files | Authenticated |
| `GET` | `/api/auth/me` | Returns current user's profile and assigned role | Authenticated |
| `GET` | `/api/admin/users` | Lists all users with status, role, and summary counts | **Admin Only** |
| `POST` | `/api/admin/users` | Creates a new user with `role="user"` | **Admin Only** |
| `DELETE` | `/api/admin/users/{id}` | Deactivates / removes user and invalidates their tokens | **Admin Only** |
| `GET` | `/api/session` | Retrieves active session state, documents, and messages | Authenticated |
| `POST` | `/api/chat` | General chat (supports SSE streaming `stream=true`) | Authenticated |
| `POST` | `/api/documents` | Uploads and processes PDF (native extraction + OCR fallback) | Authenticated |
| `GET` | `/api/documents` | Lists all documents uploaded within current session | Authenticated |
| `POST` | `/api/documents/{id}/select` | Switches active document for session | Authenticated |
| `POST` | `/api/documents/{id}/chat` | Document Q&A (supports SSE streaming `stream=true`) | Authenticated |
| `POST` | `/api/chat/clear` | Resets conversation history and active document mode | Authenticated |

---

## 6. Final Acceptance Scorecard

| Area | Status |
| :--- | :--- |
| **Authentication** | **PASS** |
| **Two-Role Model (`admin` / `user`)** | **PASS** |
| **Admin Bootstrap** | **PASS** |
| **Admin User Creation** | **PASS** |
| **Admin User Removal** | **PASS** |
| **Admin Dashboard UI** | **PASS** |
| **User AI Access** | **PASS** |
| **Admin AI Access** | **PASS** |
| **Server-Side RBAC Enforcement** | **PASS** |
| **Session Isolation** | **PASS** |
| **Data Isolation** | **PASS** |
| **Password Security (PBKDF2/Salted)** | **PASS** |
| **Multi-Client Tests** | **PASS** |
| **Regression Tests** | **PASS** |
| **Documentation** | **UPDATED** |
