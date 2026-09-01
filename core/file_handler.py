from __future__ import annotations

import logging
import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class FileHandler:
    def __init__(self, base_upload_dir: str = "uploads"):
        self.base_upload_dir = Path(base_upload_dir).resolve()
        self.base_upload_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        clean = Path(filename).name
        clean = re.sub(r'[^a-zA-Z0-9_.-]', '_', clean)
        if not clean or clean.startswith('.'):
            clean = f"document_{uuid.uuid4().hex[:8]}.pdf"
        return clean

    def get_session_dir(self, session_id: str) -> Path:
        if not session_id or re.search(r'[^a-zA-Z0-9_-]', session_id):
            raise ValueError("Invalid session ID or path traversal attempt detected")
        session_dir = (self.base_upload_dir / session_id).resolve()
        if not str(session_dir).startswith(str(self.base_upload_dir)):
            raise ValueError("Path traversal attempt detected")
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    def save_uploaded_file(
        self, session_id: str, original_filename: str, file_bytes: bytes
    ) -> tuple[str, Path]:
        sanitized_name = self.sanitize_filename(original_filename)
        doc_id = str(uuid.uuid4())
        session_dir = self.get_session_dir(session_id)
        
        target_path = session_dir / f"{doc_id}_{sanitized_name}"
        # Validate path
        if not str(target_path.resolve()).startswith(str(session_dir)):
            raise ValueError("Invalid file destination")
            
        target_path.write_bytes(file_bytes)
        logger.info("Saved file %s for session %s (ID: %s)", sanitized_name, session_id, doc_id)
        return doc_id, target_path

    def get_file_path(self, session_id: str, doc_id: str) -> Optional[Path]:
        session_dir = self.get_session_dir(session_id)
        safe_doc_id = re.sub(r'[^a-zA-Z0-9_-]', '', doc_id)
        for f in session_dir.iterdir():
            if f.is_file() and f.name.startswith(safe_doc_id):
                return f
        return None

    def delete_session_files(self, session_id: str) -> None:
        try:
            session_dir = self.get_session_dir(session_id)
            if session_dir.exists():
                shutil.rmtree(session_dir)
                logger.info("Deleted upload dir for session %s", session_id)
        except Exception as exc:
            logger.warning("Failed to delete session files for %s: %s", session_id, exc)

    def delete_all_temp_files(self) -> None:
        try:
            for child in self.base_upload_dir.iterdir():
                if child.is_dir():
                    shutil.rmtree(child)
                elif child.is_file():
                    child.unlink()
            logger.info("Cleaned up all upload directories")
        except Exception as exc:
            logger.warning("Cleanup error: %s", exc)
