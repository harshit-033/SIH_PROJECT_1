from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
import time
import uuid
from typing import Any, Callable, Dict, Optional


class RequestStatus(str, Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class RequestTask:
    task_id: str
    session_id: str
    action_type: str
    created_at: float = field(default_factory=time.time)
    status: RequestStatus = RequestStatus.QUEUED
    error_message: Optional[str] = None


class RequestQueue:
    def __init__(self, max_concurrent_inference: int = 1):
        self.semaphore = asyncio.Semaphore(max_concurrent_inference)
        self.active_count = 0
        self.queued_count = 0
        self._lock = asyncio.Lock()
        self._tasks: Dict[str, RequestTask] = {}

    def create_task(self, session_id: str, action_type: str) -> RequestTask:
        task_id = str(uuid.uuid4())
        task = RequestTask(
            task_id=task_id,
            session_id=session_id,
            action_type=action_type,
            status=RequestStatus.QUEUED,
        )
        self._tasks[task_id] = task
        return task

    async def acquire_slot(self, task: RequestTask):
        async with self._lock:
            self.queued_count += 1
        await self.semaphore.acquire()
        async with self._lock:
            self.queued_count -= 1
            self.active_count += 1
            task.status = RequestStatus.PROCESSING

    async def release_slot(self, task: RequestTask, success: bool = True, error: Optional[str] = None):
        try:
            self.semaphore.release()
        finally:
            async with self._lock:
                self.active_count = max(0, self.active_count - 1)
                task.status = RequestStatus.COMPLETED if success else RequestStatus.FAILED
                task.error_message = error

    def get_stats(self) -> Dict[str, Any]:
        return {
            "active_requests": self.active_count,
            "queued_requests": self.queued_count,
            "inference_worker_busy": self.active_count > 0,
        }
