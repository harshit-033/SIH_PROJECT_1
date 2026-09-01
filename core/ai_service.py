from __future__ import annotations

import logging
import time
from typing import Any, Dict, Generator, List, Optional

import ollama

logger = logging.getLogger(__name__)

DEFAULT_MODEL_NAME = "llama3.2:latest"
SYSTEM_PROMPT_CONTENT = (
    "You are a helpful offline AI assistant running locally. "
    "Answer clearly and do not claim to use online services."
)


class AIService:
    def __init__(self, model_name: str = DEFAULT_MODEL_NAME):
        self.model_name = model_name

    def check_health(self) -> Dict[str, Any]:
        try:
            models_info = ollama.list()
            # ollama.list() returns a dict or ListResponse with 'models'
            models = getattr(models_info, "models", None)
            if models is None and isinstance(models_info, dict):
                models = models_info.get("models", [])
            
            model_names = []
            if models:
                for m in models:
                    name = getattr(m, "model", None) or getattr(m, "name", None)
                    if not name and isinstance(m, dict):
                        name = m.get("model") or m.get("name")
                    if name:
                        model_names.append(name)
            
            # Check if our model name matches any installed model
            is_available = any(
                self.model_name in name or name.startswith(self.model_name.split(":")[0])
                for name in model_names
            )
            return {
                "connected": True,
                "model_configured": self.model_name,
                "model_available": is_available,
                "available_models": model_names,
            }
        except Exception as exc:
            logger.warning("Ollama health check failed: %s", exc)
            return {
                "connected": False,
                "model_configured": self.model_name,
                "model_available": False,
                "error": str(exc),
            }

    def generate_chat_stream(
        self, messages: List[Dict[str, str]]
    ) -> Generator[str, None, float]:
        started_at = time.perf_counter()
        stream = ollama.chat(model=self.model_name, messages=messages, stream=True)
        for chunk in stream:
            piece = ""
            if isinstance(chunk, dict):
                piece = chunk.get("message", {}).get("content", "")
            else:
                msg = getattr(chunk, "message", None)
                if msg:
                    piece = getattr(msg, "content", "")
            if piece:
                yield piece
        elapsed = time.perf_counter() - started_at
        return elapsed

    def generate_chat(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        started_at = time.perf_counter()
        response = ollama.chat(model=self.model_name, messages=messages, stream=False)
        elapsed = time.perf_counter() - started_at
        
        content = ""
        if isinstance(response, dict):
            content = response.get("message", {}).get("content", "")
        else:
            msg = getattr(response, "message", None)
            if msg:
                content = getattr(msg, "content", "")
                
        return {
            "content": content,
            "latency_seconds": elapsed,
            "model": self.model_name,
        }
