from __future__ import annotations

import psutil
from typing import Any, Dict

from .models import SystemMetrics


class MonitoringService:
    @staticmethod
    def get_metrics(
        active_requests: int = 0,
        queued_requests: int = 0,
        inference_worker_busy: bool = False,
        ollama_connected: bool = True,
        model_available: bool = True,
    ) -> SystemMetrics:
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        
        return SystemMetrics(
            cpu_percent=cpu,
            memory_percent=mem.percent,
            memory_used_mb=round(mem.used / (1024 * 1024), 1),
            memory_total_mb=round(mem.total / (1024 * 1024), 1),
            active_requests=active_requests,
            queued_requests=queued_requests,
            inference_worker_busy=inference_worker_busy,
            ollama_connected=ollama_connected,
            model_available=model_available,
        )
