"""Titan SDK Reliability Framework.

Provides safe execution wrappers for heartbeat loops, diagnostics, background
tasks, scheduler jobs, and command handlers. The goal is simple: failures should
be reported, not allowed to silently kill platform services.
"""
from __future__ import annotations

import functools
import threading
import time
import traceback
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from .runtime import utc_now_iso


@dataclass
class ReliabilityEvent:
    name: str
    status: str
    started_at: str = field(default_factory=utc_now_iso)
    finished_at: str = ""
    duration_ms: int = 0
    error: str = ""
    traceback: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def finish(self, status: str, error: Optional[BaseException] = None):
        self.finished_at = utc_now_iso()
        self.status = status
        if error is not None:
            self.error = str(error)
            self.traceback = traceback.format_exc()
        return self

    def to_dict(self):
        return {
            "name": self.name,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "traceback": self.traceback,
            "metadata": self.metadata,
        }


class ReliabilityMonitor:
    def __init__(self, client=None):
        self.client = client
        self.events = []
        self.failures = 0
        self.successes = 0
        self.last_error = ""
        self.last_event = None
        self._lock = threading.Lock()

    def record(self, event: ReliabilityEvent):
        with self._lock:
            self.last_event = event.to_dict()
            self.events.append(self.last_event)
            self.events = self.events[-100:]
            if event.status == "success":
                self.successes += 1
            else:
                self.failures += 1
                self.last_error = event.error
        return self.last_event

    def snapshot(self):
        with self._lock:
            total = self.successes + self.failures
            success_rate = round((self.successes / total) * 100, 2) if total else 100.0
            return {
                "successes": self.successes,
                "failures": self.failures,
                "success_rate": success_rate,
                "last_error": self.last_error,
                "last_event": self.last_event,
                "recent_events": list(self.events[-10:]),
            }


def safe_call(func: Callable, *args: Any, default: Any = None, logger: Any = None, name: Optional[str] = None, **kwargs: Any):
    try:
        return func(*args, **kwargs)
    except Exception as error:
        if logger:
            try:
                logger.error("%s failed: %s", name or getattr(func, "__name__", "call"), error)
            except Exception:
                pass
        return default


def safe_task(name: Optional[str] = None, client=None, reraise: bool = False, default: Any = None):
    """Decorator for background tasks and scheduler jobs."""
    def decorator(func: Callable):
        task_name = name or getattr(func, "__name__", "task")

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            started = time.time()
            event = ReliabilityEvent(name=task_name, status="running")
            active_client = client or getattr(args[0], "client", None) if args else client
            try:
                result = func(*args, **kwargs)
                event.duration_ms = int((time.time() - started) * 1000)
                event.finish("success")
                if active_client and hasattr(active_client, "record_reliability_event"):
                    active_client.record_reliability_event(event)
                return result
            except Exception as error:
                event.duration_ms = int((time.time() - started) * 1000)
                event.finish("error", error)
                if active_client and hasattr(active_client, "record_reliability_event"):
                    active_client.record_reliability_event(event)
                if active_client and hasattr(active_client, "logger"):
                    try:
                        active_client.logger.error("Task %s failed: %s", task_name, error)
                    except Exception:
                        pass
                if reraise:
                    raise
                return default

        return wrapper
    return decorator


def safe_background_task(*args, **kwargs):
    return safe_task(*args, **kwargs)


def safe_scheduler(*args, **kwargs):
    return safe_task(*args, **kwargs)


def safe_heartbeat(func: Callable):
    """Decorator used by heartbeat loops so one bad diagnostics call cannot kill the thread."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as error:
            client = args[0] if args else None
            if hasattr(client, "_handle_callback_error"):
                client._handle_callback_error("heartbeat_loop", error)
            elif hasattr(client, "logger"):
                try:
                    client.logger.error("Heartbeat loop failed: %s", error)
                except Exception:
                    pass
            return False
    return wrapper
