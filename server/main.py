from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    Header,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.ai_service import AIService, DEFAULT_MODEL_NAME
from core.auth import AuthService, hash_password, verify_password
from core.document_service import DocumentService
from core.file_handler import FileHandler
from core.models import AppMode, AuthToken, DocumentMetadata, UserCredentials, UserModel, UserRole
from core.monitoring import MonitoringService
from core.request_queue import RequestQueue
from core.session_manager import SessionManager
from core.user_store import UserStore

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sih_server")

app = FastAPI(
    title="SIH Local AI Workbench Server",
    description="Multi-Client Local AI Server with Admin + User RBAC",
    version="2.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

user_store = UserStore(storage_path=str(PROJECT_ROOT / "data" / "users.json"))
auth_service = AuthService(user_store=user_store)
ai_service = AIService()
doc_service = DocumentService()
file_handler = FileHandler(base_upload_dir=str(PROJECT_ROOT / "uploads"))
session_manager = SessionManager()
request_queue = RequestQueue(max_concurrent_inference=1)
monitoring_service = MonitoringService()


# -------------------------------------------------------------
# Request & Response Schemas
# -------------------------------------------------------------
class LoginRequest(BaseModel):
    username: str
    password: str


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=4, max_length=128)


class UpdateUsernameRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=4, max_length=128)
    confirm_password: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    message: str
    stream: bool = True


class SelectDocRequest(BaseModel):
    document_id: str


# -------------------------------------------------------------
# Authentication & RBAC Dependencies
# -------------------------------------------------------------
async def require_authenticated_user(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> tuple[str, str, str, UserRole, UserModel]:
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[len("Bearer "):]
    elif "token" in request.query_params:
        token = request.query_params["token"]

    if not token:
        # Check for test / development header
        anon_session = request.headers.get("X-Session-ID") or request.query_params.get("session_id")
        if anon_session:
            session = session_manager.get_session(anon_session)
            if session:
                user = user_store.get_user_by_id(session.user_id)
                if user and user.is_active:
                    return session.session_id, user.id, user.username, user.role, user

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
        )

    auth_token = auth_service.validate_token(token)
    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token.",
        )

    user = user_store.get_user_by_id(auth_token.user_id)
    if not user or not user.is_active:
        auth_service.revoke_token(token)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is inactive or no longer exists.",
        )

    session = session_manager.get_session(auth_token.token)
    if not session:
        session = session_manager.create_session(
            user_id=user.id, username=user.username
        )
        session.role = user.role
        session_manager._sessions[auth_token.token] = session

    return session.session_id, user.id, user.username, user.role, user


async def require_admin(
    current: tuple[str, str, str, UserRole, UserModel] = Depends(require_authenticated_user),
) -> UserModel:
    _, _, username, role, user = current
    if role != UserRole.ADMIN and role != "admin":
        logger.warning("Access denied: User '%s' lacks admin privileges for admin endpoint", username)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privilege required to perform this action.",
        )
    return user


# -------------------------------------------------------------
# Routes: Health & Metrics
# -------------------------------------------------------------
@app.get("/health")
async def health_check():
    ai_health = ai_service.check_health()
    ocr_health = doc_service.check_ocr_availability()
    queue_stats = request_queue.get_stats()
    metrics = monitoring_service.get_metrics(
        active_requests=queue_stats["active_requests"],
        queued_requests=queue_stats["queued_requests"],
        inference_worker_busy=queue_stats["inference_worker_busy"],
        ollama_connected=ai_health["connected"],
        model_available=ai_health["model_available"],
    )

    return {
        "status": "healthy" if ai_health["connected"] else "degraded",
        "timestamp": time.time(),
        "ai_service": ai_health,
        "ocr_service": ocr_health,
        "queue": queue_stats,
        "metrics": {
            "cpu_percent": metrics.cpu_percent,
            "memory_percent": metrics.memory_percent,
            "memory_used_mb": metrics.memory_used_mb,
            "memory_total_mb": metrics.memory_total_mb,
        },
    }


@app.get("/api/metrics")
async def get_metrics():
    queue_stats = request_queue.get_stats()
    ai_health = ai_service.check_health()
    metrics = monitoring_service.get_metrics(
        active_requests=queue_stats["active_requests"],
        queued_requests=queue_stats["queued_requests"],
        inference_worker_busy=queue_stats["inference_worker_busy"],
        ollama_connected=ai_health["connected"],
        model_available=ai_health["model_available"],
    )
    return {
        "metrics": metrics,
        "queue": queue_stats,
        "ai": ai_health,
    }


# -------------------------------------------------------------
# Routes: Authentication & User Profile
# -------------------------------------------------------------
@app.post("/api/auth/login")
async def login(creds: LoginRequest):
    token = auth_service.authenticate(
        UserCredentials(username=creds.username, password=creds.password)
    )
    if token == "ADMIN_ALREADY_ACTIVE":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Admin account is already logged in on another system.",
        )
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    session = session_manager.create_session(
        user_id=token.user_id, username=token.username
    )
    session.role = token.role
    session_manager._sessions[token.token] = session

    return {
        "token": token.token,
        "user_id": token.user_id,
        "username": token.username,
        "role": token.role.value if isinstance(token.role, UserRole) else str(token.role),
        "expires_at": token.expires_at,
        "session_id": session.session_id,
    }


@app.post("/api/auth/logout")
async def logout(
    current: tuple[str, str, str, UserRole, UserModel] = Depends(require_authenticated_user),
):
    session_id, user_id, username, _, _ = current
    for tok_str, sess in list(session_manager._sessions.items()):
        if sess.session_id == session_id:
            auth_service.revoke_token(tok_str)
            session_manager.delete_session(tok_str)

    file_handler.delete_session_files(session_id)
    logger.info("User '%s' logged out (Session: %s)", username, session_id)
    return {"message": "Successfully logged out."}


@app.get("/api/auth/me")
async def get_current_user_profile(
    current: tuple[str, str, str, UserRole, UserModel] = Depends(require_authenticated_user),
):
    _, _, _, _, user = current
    return user.to_safe_dict()


# -------------------------------------------------------------
# Routes: Admin User Management
# -------------------------------------------------------------
@app.get("/api/admin/users")
async def list_users(admin: UserModel = Depends(require_admin)):
    users = user_store.list_users()
    total_count = len(users)
    active_count = sum(1 for u in users if u.is_active)
    admin_count = sum(1 for u in users if u.role == UserRole.ADMIN and u.is_active)

    return {
        "summary": {
            "total_users": total_count,
            "active_users": active_count,
            "admin_users": admin_count,
        },
        "users": [u.to_safe_dict() for u in users],
    }


@app.post("/api/admin/users")
async def create_user(
    req: CreateUserRequest,
    admin: UserModel = Depends(require_admin),
):
    clean_username = req.username.strip()
    if not clean_username:
        raise HTTPException(status_code=400, detail="Username cannot be empty.")

    if user_store.get_user_by_username(clean_username):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{clean_username}' already exists.",
        )

    pw_hash = hash_password(req.password)
    try:
        new_user = user_store.create_user(
            username=clean_username,
            password_hash=pw_hash,
            role=UserRole.USER,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    logger.info("Admin '%s' created new user '%s' (ID: %s)", admin.username, new_user.username, new_user.id)
    return {
        "message": f"User '{new_user.username}' created successfully.",
        "user": new_user.to_safe_dict(),
    }


@app.delete("/api/admin/users/{user_id}")
async def remove_user(
    user_id: str,
    admin: UserModel = Depends(require_admin),
):
    target = user_store.get_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")

    if target.id == admin.id or target.username.lower() == admin.username.lower():
        raise HTTPException(
            status_code=400,
            detail="Admin cannot remove their own account through the management interface.",
        )

    try:
        user_store.remove_user(user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Invalidate all active tokens for this user
    auth_service.revoke_user_tokens(user_id)

    # Invalidate active sessions
    for tok_str, sess in list(session_manager._sessions.items()):
        if sess.user_id == user_id:
            session_manager.delete_session(tok_str)
            file_handler.delete_session_files(sess.session_id)

    logger.info("Admin '%s' removed user '%s' (ID: %s)", admin.username, target.username, user_id)
    return {"message": f"User '{target.username}' removed successfully."}


# -------------------------------------------------------------
# Routes: Admin Profile Self-Management ("My Account")
# -------------------------------------------------------------
@app.patch("/api/admin/me")
@app.patch("/admin/me")
async def update_admin_username(
    req: UpdateUsernameRequest,
    admin: UserModel = Depends(require_admin),
):
    clean_username = req.username.strip()
    if not clean_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username cannot be empty.",
        )

    try:
        updated = user_store.update_username(admin.id, clean_username)
    except ValueError as exc:
        msg = str(exc)
        if "already taken" in msg.lower() or "already exists" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=msg,
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )

    # Sync username in any active sessions for this admin
    for sess in session_manager._sessions.values():
        if sess.user_id == admin.id:
            sess.username = updated.username

    logger.info("Admin updated username to '%s' (ID: %s)", updated.username, admin.id)
    return {
        "message": "Username updated successfully.",
        "user": updated.to_safe_dict(),
    }


@app.post("/api/admin/me/change-password")
@app.post("/admin/me/change-password")
async def change_admin_password(
    req: ChangePasswordRequest,
    admin: UserModel = Depends(require_admin),
):
    if not req.current_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is required.",
        )

    # Verify current password
    if not verify_password(req.current_password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )

    # Check new password confirmation
    if req.new_password != req.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirmation do not match.",
        )

    if len(req.new_password) < 4:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 4 characters long.",
        )

    new_hash = hash_password(req.new_password)
    user_store.update_password_hash(admin.id, new_hash)

    logger.info("Admin '%s' (ID: %s) changed password successfully.", admin.username, admin.id)
    return {"message": "Password changed successfully."}


# -------------------------------------------------------------
# Routes: Session Management
# -------------------------------------------------------------
@app.get("/api/session")
async def get_session_info(
    current: tuple[str, str, str, UserRole, UserModel] = Depends(require_authenticated_user),
):
    session_id, _, username, role, _ = current
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    docs = [d.to_dict() for d in session.uploaded_documents.values()]

    context_info = None
    if session.current_document_context:
        ctx = session.current_document_context
        context_info = {
            "included_pages": ctx.included_pages,
            "total_text_pages": ctx.total_text_pages,
            "truncated": ctx.truncated,
            "estimated_tokens": ctx.estimated_tokens,
        }

    return {
        "session_id": session.session_id,
        "username": session.username,
        "role": role.value if isinstance(role, UserRole) else str(role),
        "mode": session.mode.value,
        "current_document_id": session.current_document_id,
        "current_document_context": context_info,
        "uploaded_documents": docs,
        "general_messages": [m for m in session.general_messages if m["role"] != "system"],
        "document_messages": [m for m in session.document_messages if m["role"] != "system"],
    }


@app.post("/api/chat/clear")
async def clear_chat(
    current: tuple[str, str, str, UserRole, UserModel] = Depends(require_authenticated_user),
):
    session_id, _, _, _, _ = current
    session_manager.clear_session_chat(session_id)
    return {"message": "Chat and active document state cleared", "mode": AppMode.GENERAL_CHAT.value}


# -------------------------------------------------------------
# Routes: General Chat
# -------------------------------------------------------------
@app.post("/api/chat")
async def general_chat(
    req: ChatRequest,
    current: tuple[str, str, str, UserRole, UserModel] = Depends(require_authenticated_user),
):
    session_id, _, username, _, _ = current
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    user_msg = req.message.strip()
    if not user_msg:
        raise HTTPException(status_code=400, detail="Empty prompt")

    task = request_queue.create_task(session_id, "general_chat")

    if not req.stream:
        await request_queue.acquire_slot(task)
        try:
            messages = session_manager.get_messages(session_id, AppMode.GENERAL_CHAT)
            messages.append({"role": "user", "content": user_msg})
            result = ai_service.generate_chat(messages)

            session_manager.add_message(session_id, AppMode.GENERAL_CHAT, "user", user_msg)
            session_manager.add_message(session_id, AppMode.GENERAL_CHAT, "assistant", result["content"])
            await request_queue.release_slot(task, success=True)
            return result
        except Exception as exc:
            await request_queue.release_slot(task, success=False, error=str(exc))
            raise HTTPException(status_code=500, detail=f"Inference error: {exc}")

    async def sse_generator():
        await request_queue.acquire_slot(task)
        collected_chunks = []
        try:
            yield f"data: {json.dumps({'type': 'status', 'status': 'processing'})}\n\n"
            messages = session_manager.get_messages(session_id, AppMode.GENERAL_CHAT)
            messages.append({"role": "user", "content": user_msg})

            started_at = time.perf_counter()
            loop = asyncio.get_event_loop()

            def run_sync_stream():
                return list(ai_service.generate_chat_stream(messages))

            chunks = await loop.run_in_executor(None, run_sync_stream)
            for chunk in chunks:
                collected_chunks.append(chunk)
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
                await asyncio.sleep(0.01)

            elapsed = time.perf_counter() - started_at
            full_response = "".join(collected_chunks)
            session_manager.add_message(session_id, AppMode.GENERAL_CHAT, "user", user_msg)
            session_manager.add_message(session_id, AppMode.GENERAL_CHAT, "assistant", full_response)

            yield f"data: {json.dumps({'type': 'done', 'latency_seconds': round(elapsed, 2)})}\n\n"
            await request_queue.release_slot(task, success=True)
        except Exception as exc:
            logger.exception("Error during general chat streaming: %s", exc)
            yield f"data: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n"
            await request_queue.release_slot(task, success=False, error=str(exc))

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


# -------------------------------------------------------------
# Routes: Document Upload & Management
# -------------------------------------------------------------
@app.post("/api/documents")
async def upload_document(
    file: UploadFile = File(...),
    current: tuple[str, str, str, UserRole, UserModel] = Depends(require_authenticated_user),
):
    session_id, _, _, _, _ = current
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        doc_id, saved_path = file_handler.save_uploaded_file(
            session_id=session_id,
            original_filename=file.filename,
            file_bytes=content,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to save file: {exc}")

    try:
        extraction = doc_service.process_pdf(str(saved_path))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.exception("Extraction failed: %s", exc)
        raise HTTPException(status_code=400, detail="The selected PDF could not be read.")

    context = doc_service.create_context(extraction.pages)

    meta = DocumentMetadata(
        document_id=doc_id,
        session_id=session_id,
        filename=file.filename,
        stored_path=str(saved_path),
        page_count=extraction.page_count,
        extracted_chars=extraction.extracted_chars,
        file_size_mb=extraction.file_size_mb,
        extraction_seconds=extraction.extraction_seconds,
        native_pages=extraction.native_pages,
        ocr_pages=extraction.ocr_pages,
        method_summary=extraction.method_summary,
    )

    session_manager.add_document(
        session_id=session_id,
        doc_meta=meta,
        extraction=extraction,
        context=context,
    )

    return {
        "message": "Document processed successfully",
        "document": meta.to_dict(),
        "context": {
            "included_pages": context.included_pages,
            "total_text_pages": context.total_text_pages,
            "truncated": context.truncated,
            "estimated_tokens": context.estimated_tokens,
        },
        "mode": session.mode.value,
    }


@app.get("/api/documents")
async def list_documents(
    current: tuple[str, str, str, UserRole, UserModel] = Depends(require_authenticated_user),
):
    session_id, _, _, _, _ = current
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"documents": [d.to_dict() for d in session.uploaded_documents.values()]}


@app.post("/api/documents/{document_id}/select")
async def select_document(
    document_id: str,
    current: tuple[str, str, str, UserRole, UserModel] = Depends(require_authenticated_user),
):
    session_id, _, _, _, _ = current
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session_manager.verify_document_ownership(session_id, document_id):
        raise HTTPException(status_code=403, detail="Document does not belong to this session.")

    meta = session.uploaded_documents[document_id]
    extraction = doc_service.process_pdf(meta.stored_path)
    context = doc_service.create_context(extraction.pages)

    session_manager.select_document(session_id, document_id, extraction, context)

    return {
        "message": f"Selected document {meta.filename}",
        "document": meta.to_dict(),
        "mode": session.mode.value,
    }


@app.post("/api/documents/{document_id}/chat")
async def document_chat(
    document_id: str,
    req: ChatRequest,
    current: tuple[str, str, str, UserRole, UserModel] = Depends(require_authenticated_user),
):
    session_id, _, _, _, _ = current
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if not session_manager.verify_document_ownership(session_id, document_id):
        raise HTTPException(status_code=403, detail="Document not found or access denied.")

    user_msg = req.message.strip()
    if not user_msg:
        raise HTTPException(status_code=400, detail="Empty question")

    if not session.current_document_context or not session.current_document_context.text:
        raise HTTPException(status_code=400, detail="No readable document text available.")

    task = request_queue.create_task(session_id, f"doc_chat_{document_id}")

    formatted_prompt = doc_service.format_prompt(
        user_question=user_msg,
        context_text=session.current_document_context.text,
    )

    if not req.stream:
        await request_queue.acquire_slot(task)
        try:
            messages = session_manager.get_messages(session_id, AppMode.DOCUMENT_ANALYSIS)
            messages.append({"role": "user", "content": formatted_prompt})
            result = ai_service.generate_chat(messages)

            session_manager.add_message(session_id, AppMode.DOCUMENT_ANALYSIS, "user", user_msg)
            session_manager.add_message(session_id, AppMode.DOCUMENT_ANALYSIS, "assistant", result["content"])
            await request_queue.release_slot(task, success=True)
            return result
        except Exception as exc:
            await request_queue.release_slot(task, success=False, error=str(exc))
            raise HTTPException(status_code=500, detail=f"Inference error: {exc}")

    async def sse_generator():
        await request_queue.acquire_slot(task)
        collected_chunks = []
        try:
            yield f"data: {json.dumps({'type': 'status', 'status': 'processing'})}\n\n"
            messages = session_manager.get_messages(session_id, AppMode.DOCUMENT_ANALYSIS)
            messages.append({"role": "user", "content": formatted_prompt})

            started_at = time.perf_counter()
            loop = asyncio.get_event_loop()

            def run_sync_stream():
                return list(ai_service.generate_chat_stream(messages))

            chunks = await loop.run_in_executor(None, run_sync_stream)
            for chunk in chunks:
                collected_chunks.append(chunk)
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
                await asyncio.sleep(0.01)

            elapsed = time.perf_counter() - started_at
            full_response = "".join(collected_chunks)
            session_manager.add_message(session_id, AppMode.DOCUMENT_ANALYSIS, "user", user_msg)
            session_manager.add_message(session_id, AppMode.DOCUMENT_ANALYSIS, "assistant", full_response)

            yield f"data: {json.dumps({'type': 'done', 'latency_seconds': round(elapsed, 2)})}\n\n"
            await request_queue.release_slot(task, success=True)
        except Exception as exc:
            logger.exception("Error during document chat streaming: %s", exc)
            yield f"data: {json.dumps({'type': 'error', 'error': str(exc)})}\n\n"
            await request_queue.release_slot(task, success=False, error=str(exc))

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


# -------------------------------------------------------------
# Static Files & Frontend Serving
# -------------------------------------------------------------
STATIC_DIR = PROJECT_ROOT / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>SIH Local AI Workbench Server is Running</h1>")
