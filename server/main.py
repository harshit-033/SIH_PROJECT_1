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
from pydantic import BaseModel

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.ai_service import AIService, DEFAULT_MODEL_NAME
from core.auth import AuthService
from core.document_service import DocumentService
from core.file_handler import FileHandler
from core.models import AppMode, DocumentMetadata, UserCredentials
from core.monitoring import MonitoringService
from core.request_queue import RequestQueue
from core.session_manager import SessionManager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sih_server")

app = FastAPI(
    title="SIH Local AI Workbench Server",
    description="Multi-Client Local AI Server for Offline Document Analysis & Chat",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ai_service = AIService()
doc_service = DocumentService()
file_handler = FileHandler(base_upload_dir=str(PROJECT_ROOT / "uploads"))
session_manager = SessionManager()
auth_service = AuthService()
request_queue = RequestQueue(max_concurrent_inference=1)
monitoring_service = MonitoringService()

class LoginRequest(BaseModel):
    username: str
    password: str

class ChatRequest(BaseModel):
    message: str
    stream: bool = True

class SelectDocRequest(BaseModel):
    document_id: str

async def get_current_session(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> tuple[str, str]:
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[len("Bearer "):]
    elif "token" in request.query_params:
        token = request.query_params["token"]

    if not token:
        anon_session = request.headers.get("X-Session-ID") or request.query_params.get("session_id")
        if anon_session:
            session = session_manager.get_session(anon_session)
            if session:
                return session.session_id, session.username

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

    session = session_manager.get_session(auth_token.token)
    if not session:
        session = session_manager.create_session(
            user_id=auth_token.user_id, username=auth_token.username
        )
        session_manager._sessions[auth_token.token] = session

    return session.session_id, auth_token.username


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


@app.post("/api/auth/login")
async def login(creds: LoginRequest):
    token = auth_service.authenticate(
        UserCredentials(username=creds.username, password=creds.password)
    )
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    session = session_manager.create_session(
        user_id=token.user_id, username=token.username
    )
    session_manager._sessions[token.token] = session

    return {
        "token": token.token,
        "user_id": token.user_id,
        "username": token.username,
        "expires_at": token.expires_at,
        "session_id": session.session_id,
    }


@app.post("/api/auth/logout")
async def logout(current: tuple[str, str] = Depends(get_current_session)):
    session_id, username = current
    for tok_str, sess in list(session_manager._sessions.items()):
        if sess.session_id == session_id:
            auth_service.revoke_token(tok_str)
            session_manager.delete_session(tok_str)
    
    file_handler.delete_session_files(session_id)
    return {"message": "Successfully logged out."}


@app.get("/api/session")
async def get_session_info(current: tuple[str, str] = Depends(get_current_session)):
    session_id, username = current
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
        "mode": session.mode.value,
        "current_document_id": session.current_document_id,
        "current_document_context": context_info,
        "uploaded_documents": docs,
        "general_messages": [m for m in session.general_messages if m["role"] != "system"],
        "document_messages": [m for m in session.document_messages if m["role"] != "system"],
    }


@app.post("/api/chat/clear")
async def clear_chat(current: tuple[str, str] = Depends(get_current_session)):
    session_id, _ = current
    session_manager.clear_session_chat(session_id)
    return {"message": "Chat and active document state cleared", "mode": AppMode.GENERAL_CHAT.value}


@app.post("/api/chat")
async def general_chat(
    req: ChatRequest, current: tuple[str, str] = Depends(get_current_session)
):
    session_id, username = current
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


@app.post("/api/documents")
async def upload_document(
    file: UploadFile = File(...),
    current: tuple[str, str] = Depends(get_current_session),
):
    session_id, _ = current
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
async def list_documents(current: tuple[str, str] = Depends(get_current_session)):
    session_id, _ = current
    session = session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"documents": [d.to_dict() for d in session.uploaded_documents.values()]}


@app.post("/api/documents/{document_id}/select")
async def select_document(
    document_id: str, current: tuple[str, str] = Depends(get_current_session)
):
    session_id, _ = current
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
    current: tuple[str, str] = Depends(get_current_session),
):
    session_id, _ = current
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


STATIC_DIR = PROJECT_ROOT / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>SIH Local AI Workbench Server is Running</h1>")
