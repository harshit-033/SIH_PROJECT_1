from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from document.models import DocumentContext, DocumentExtraction, PageBlock


class AppMode(str, Enum):
    GENERAL_CHAT = "General Chat"
    DOCUMENT_ANALYSIS = "Document Analysis"


@dataclass
class ChatMessage:
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)


@dataclass
class DocumentMetadata:
    document_id: str
    session_id: str
    filename: str
    stored_path: str
    page_count: int
    extracted_chars: int
    file_size_mb: float
    extraction_seconds: float
    native_pages: int
    ocr_pages: int
    method_summary: str
    uploaded_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "session_id": self.session_id,
            "filename": self.filename,
            "page_count": self.page_count,
            "extracted_chars": self.extracted_chars,
            "file_size_mb": round(self.file_size_mb, 2),
            "extraction_seconds": round(self.extraction_seconds, 2),
            "native_pages": self.native_pages,
            "ocr_pages": self.ocr_pages,
            "method_summary": self.method_summary,
            "uploaded_at": self.uploaded_at,
        }


@dataclass
class SessionData:
    session_id: str
    user_id: str
    username: str
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    mode: AppMode = AppMode.GENERAL_CHAT
    general_messages: List[Dict[str, str]] = field(default_factory=list)
    document_messages: List[Dict[str, str]] = field(default_factory=list)
    uploaded_documents: Dict[str, DocumentMetadata] = field(default_factory=dict)
    current_document_id: Optional[str] = None
    current_document_extraction: Optional[DocumentExtraction] = None
    current_document_context: Optional[DocumentContext] = None


@dataclass
class SystemMetrics:
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    active_requests: int
    queued_requests: int
    inference_worker_busy: bool
    ollama_connected: bool
    model_available: bool


@dataclass
class UserCredentials:
    username: str
    password: str


@dataclass
class AuthToken:
    token: str
    user_id: str
    username: str
    expires_at: float
