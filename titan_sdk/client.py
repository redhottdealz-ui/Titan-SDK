import os
import platform
import sys
import time
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

import requests

from .constants import (
    DEFAULT_HEARTBEAT_INTERVAL,
    DEFAULT_QUEUE_FLUSH_INTERVAL,
    DEFAULT_RETRY_BASE_DELAY,
    DEFAULT_RETRY_MAX_ATTEMPTS,
    DEFAULT_RETRY_MAX_DELAY,
    DEFAULT_TIMEOUT,
    SDK_NAME,
)
from .diagnostics import build_diagnostics
from .logger import build_logger
from .operations import OperationRegistry, default_operations
from .retry import RetryQueue
from .runtime import get_hostname, uptime_seconds, utc_now_iso
from .version import SDK_VERSION


@dataclass
class TitanJob:
    client: "TitanClient"
    name: str
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        self.started_at = time.time()
        self.started_at_iso = utc_now_iso()
        self.finished = False
        self.client.increment("jobs_started")
        self.client.set_gauge(f"job_{self.name}_running", 1)

    def elapsed_seconds(self):
        return round(time.time() - self.started_at, 2)

    def success(self, message=None, metrics=None, publish_event=True):
        if self.finished:
            return self.elapsed_seconds()

        elapsed = self.elapsed_seconds()
        self.finished = True
        self.client.increment("jobs_completed")
        self.client.set_gauge(f"job_{self.name}_running", 0)
        self.client.record_timer(self.name, elapsed)
        self.client.last_successful_job = {
            "name": self.name,
            "message": message or "Job completed successfully.",
            "elapsed_seconds": elapsed,
            "finished_at": utc_now_iso(),
            "metadata": self.metadata or {},
        }

        if metrics:
            self.client.merge_metrics(metrics)

        if publish_event:
            self.client.event(
                f"{self.name} completed",
                message or f"{self.name} completed in {elapsed} seconds.",
                level="success",
            )

        return elapsed

    def fail(self, error, message=None, metrics=None, publish_event=True):
        if self.finished:
            return self.elapsed_seconds()

        elapsed = self.elapsed_seconds()
        self.finished = True
        error_text = str(error)
        self.client.increment("jobs_failed")
        self.client.increment("errors")
        self.client.set_gauge(f"job_{self.name}_running", 0)
        self.client.record_timer(self.name, elapsed)
        self.client.last_failed_job = {
            "name": self.name,
            "message": message or error_text,
            "error": error_text,
            "elapsed_seconds": elapsed,
            "finished_at": utc_now_iso(),
            "metadata": self.metadata or {},
        }

        if metrics:
            self.client.merge_metrics(metrics)

        if publish_event:
            self.client.event(
                f"{self.name} failed",
                message or f"{self.name} failed after {elapsed} seconds: {error_text}",
                level="error",
            )

        return elapsed


class TitanClient:
    def __init__(
        self,
        service_key,
        name,
        version="1.0.0",
        category="General",
        icon="⚙️",
        route=None,
        capabilities=None,
        operations=None,
        include_default_operations=True,
        base_url=None,
        api_key=None,
        heartbeat_interval=DEFAULT_HEARTBEAT_INTERVAL,
        timeout=DEFAULT_TIMEOUT,
        enabled=True,
        max_queue_size=100,
        on_start: Optional[Callable[["TitanClient"], None]] = None,
        on_stop: Optional[Callable[["TitanClient"], None]] = None,
        on_heartbeat: Optional[Callable[["TitanClient"], None]] = None,
        on_error: Optional[Callable[["TitanClient", Exception], None]] = None,
    ):
        self.service_key = service_key
        self.name = name
        self.version = version
        self.category = category
        self.icon = icon
        self.route = route or f"/services/{service_key}"
        self.capabilities = self._normalize_capabilities(capabilities)

        self.on_start = on_start
        self.on_stop = on_stop
        self.on_heartbeat = on_heartbeat
        self.on_error = on_error

        self.operation_registry = OperationRegistry()

        if include_default_operations:
            for operation in default_operations():
                self.operation_registry.add(**{
                    "operation_id": operation["id"],
                    "label": operation["label"],
                    "description": operation.get("description", ""),
                    "operation_type": operation.get("type", "action"),
                    "enabled": operation.get("enabled", False),
                    "requires_confirmation": operation.get("requires_confirmation", True),
                    "permission": operation.get("permission", "owner"),
                    "reason": operation.get("reason", ""),
                    "metadata": operation.get("metadata", {}),
                })

        for operation in operations or []:
            self.add_operation(**operation)

        self.base_url = (
            base_url
            or os.getenv("TITAN_OS_BASE_URL")
            or os.getenv("TITAN_OS_URL")
            or ""
        ).rstrip("/")

        self.api_key = api_key or os.getenv("TITAN_OS_API_KEY")

        self.heartbeat_interval = heartbeat_interval
        self.timeout = timeout
        self.enabled = enabled
        self.max_queue_size = max_queue_size

        self.hostname = get_hostname()
        self.started_at = utc_now_iso()
        self.process_started_at_epoch = time.time()
        self.sdk_name = SDK_NAME
        self.sdk_version = SDK_VERSION

        self.logger = build_logger(f"Titan SDK:{self.service_key}")

        self._running = False
        self._heartbeat_thread = None
        self._queue_thread = None
        self._queue_lock = threading.Lock()
        self._metrics_lock = threading.Lock()
        self._queue = RetryQueue(max_size=max_queue_size)

        self.last_successful_post = None
        self.last_failed_post = None
        self.last_successful_job = None
        self.last_failed_job = None
        self.successful_posts = 0
        self.failed_posts = 0
        self.events_sent = 0
        self.metrics_sent = 0
        self.heartbeats_sent = 0
        self.queue_flushes = 0
        self.queue_retries = 0
        self.queue_drops = 0
        self.start_count = 0
        self.stop_count = 0

        self.counters: Dict[str, int] = {
            "jobs_started": 0,
            "jobs_completed": 0,
            "jobs_failed": 0,
            "warnings": 0,
            "errors": 0,
            "events_sent": 0,
            "metrics_sent": 0,
            "heartbeats_sent": 0,
            "posts_successful": 0,
            "posts_failed": 0,
            "queue_flushes": 0,
            "queue_retries": 0,
            "queue_drops": 0,
            "starts": 0,
            "stops": 0,
        }
        self.gauges: Dict[str, Any] = {}
        self.timers: Dict[str, Dict[str, Any]] = {}

    def _normalize_capabilities(self, capabilities):
        defaults = ["registration", "heartbeat", "status", "metrics", "events", "diagnostics", "operations"]
        combined = []
        for item in defaults + list(capabilities or []):
            if item and item not in combined:
                combined.append(item)
        return combined

    def add_capability(self, capability):
        if capability and capability not in self.capabilities:
            self.capabilities.append(capability)
        return self.capabilities

    def add_operation(
        self,
        operation_id,
        label,
        description="",
        operation_type="action",
        enabled=False,
        requires_confirmation=True,
        permission="owner",
        reason="Remote execution is locked until Titan OS permissions are complete.",
        metadata=None,
    ):
        return self.operation_registry.add(
            operation_id=operation_id,
            label=label,
            description=description,
            operation_type=operation_type,
            enabled=enabled,
            requires_confirmation=requires_confirmation,
            permission=permission,
            reason=reason,
            metadata=metadata,
        )

    def remove_operation(self, operation_id):
        self.operation_registry.remove(operation_id)

    def clear_operations(self):
        self.operation_registry.clear()

    def operations(self):
        return self.operation_registry.all()

    def uptime_seconds(self):
        return uptime_seconds(self.started_at)

    def queue_size(self):
        with self._queue_lock:
            return self._queue.size()

    def diagnostics(self):
        diagnostics = build_diagnostics(self)
        if isinstance(diagnostics, dict):
            diagnostics.update(self.system_payload())
        return diagnostics

    def system_payload(self):
        return {
            "hostname": self.hostname,
            "platform": platform.platform(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python_version": platform.python_version(),
            "python_executable": sys.executable,
            "pid": os.getpid(),
            "cpu_count": os.cpu_count(),
            "thread_count": threading.active_count(),
        }

    def metrics_snapshot(self):
        with self._metrics_lock:
            return {
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "timers": dict(self.timers),
                "display": self.display_metrics(),
            }

    def display_metrics(self):
        return [
            {"label": "Jobs Done", "value": self.counters.get("jobs_completed", 0)},
            {"label": "Jobs Failed", "value": self.counters.get("jobs_failed", 0)},
            {"label": "Events", "value": self.events_sent},
            {"label": "Metrics", "value": self.metrics_sent},
            {"label": "Heartbeats", "value": self.heartbeats_sent},
            {"label": "Queue", "value": self.queue_size()},
        ]

    def increment(self, name, amount=1):
        with self._metrics_lock:
            self.counters[name] = int(self.counters.get(name, 0)) + int(amount)
            return self.counters[name]

    def set_gauge(self, name, value):
        with self._metrics_lock:
            self.gauges[name] = value
            return value

    def merge_metrics(self, metrics):
        with self._metrics_lock:
            for key, value in (metrics or {}).items():
                self.gauges[key] = value
        return self.metrics_snapshot()

    def record_timer(self, name, elapsed_seconds):
        elapsed = float(elapsed_seconds)
        with self._metrics_lock:
            timer = self.timers.get(name, {
                "count": 0,
                "total_seconds": 0.0,
                "average_seconds": 0.0,
                "min_seconds": elapsed,
                "max_seconds": elapsed,
                "last_seconds": elapsed,
                "last_recorded_at": utc_now_iso(),
            })
            timer["count"] += 1
            timer["total_seconds"] = round(float(timer.get("total_seconds", 0.0)) + elapsed, 2)
            timer["average_seconds"] = round(timer["total_seconds"] / timer["count"], 2)
            timer["min_seconds"] = min(float(timer.get("min_seconds", elapsed)), elapsed)
            timer["max_seconds"] = max(float(timer.get("max_seconds", elapsed)), elapsed)
            timer["last_seconds"] = elapsed
            timer["last_recorded_at"] = utc_now_iso()
            self.timers[name] = timer
            return dict(timer)

    def begin_job(self, name, metadata=None):
        return TitanJob(self, name, metadata=metadata)

    @contextmanager
    def job(self, name, metadata=None, publish_event=True):
        titan_job = self.begin_job(name, metadata=metadata)
        try:
            yield titan_job
        except Exception as error:
            titan_job.fail(error, publish_event=publish_event)
            raise
        else:
            titan_job.success(publish_event=publish_event)

    def health_payload(self):
        if not self.enabled:
            return {
                "health_status": "disabled",
                "health_message": "Titan SDK reporting is disabled.",
            }

        if not self.base_url:
            return {
                "health_status": "warning",
                "health_message": "Titan OS base URL is not configured.",
            }

        if not self.api_key:
            return {
                "health_status": "warning",
                "health_message": "Titan OS API key is not configured.",
            }

        if self.queue_size() > 0:
            return {
                "health_status": "warning",
                "health_message": f"{self.queue_size()} request(s) waiting in SDK retry queue.",
            }

        if self.counters.get("errors", 0) > 0:
            return {
                "health_status": "warning",
                "health_message": f"Service has reported {self.counters.get('errors', 0)} error(s) since startup.",
            }

        return {
            "health_status": "healthy",
            "health_message": "Service is operating normally.",
        }

    def runtime_payload(self):
        return {
            "hostname": self.hostname,
            "started_at": self.started_at,
            "process_started_at_epoch": self.process_started_at_epoch,
            "sdk_name": self.sdk_name,
            "sdk_version": self.sdk_version,
            "application_version": self.version,
            "uptime_seconds": self.uptime_seconds(),
            "queue_size": self.queue_size(),
            "successful_posts": self.successful_posts,
            "failed_posts": self.failed_posts,
            "events_sent": self.events_sent,
            "metrics_sent": self.metrics_sent,
            "heartbeats_sent": self.heartbeats_sent,
            "queue_flushes": self.queue_flushes,
            "queue_retries": self.queue_retries,
            "queue_drops": self.queue_drops,
            "last_successful_post": self.last_successful_post,
            "last_failed_post": self.last_failed_post,
            "last_successful_job": self.last_successful_job,
            "last_failed_job": self.last_failed_job,
            "operations": self.operations(),
            "capabilities": self.capabilities,
            "runtime_metrics": self.metrics_snapshot(),
            "system": self.system_payload(),
            **self.health_payload(),
        }

    def is_ready(self):
        return bool(self.enabled and self.base_url and self.api_key)

    def config_report(self):
        return {
            "enabled": self.enabled,
            "base_url_configured": bool(self.base_url),
            "api_key_configured": bool(self.api_key),
            "service_key": self.service_key,
            "name": self.name,
            "sdk_version": self.sdk_version,
            "application_version": self.version,
            "capabilities": self.capabilities,
            "operations_registered": len(self.operations()),
        }

    def _headers(self):
        return {
            "Content-Type": "application/json",
            "X-Titan-API-Key": self.api_key or "",
        }

    def _url(self, path):
        return f"{self.base_url}{path}"

    def _handle_callback_error(self, callback_name, error):
        self.increment("errors")
        self.logger.error("%s callback failed: %s", callback_name, error)
        if self.on_error:
            try:
                self.on_error(self, error)
            except Exception as nested_error:
                self.logger.error("on_error callback failed: %s", nested_error)

    def _send_now(self, path, payload):
        response = requests.post(
            self._url(path),
            json=payload,
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()

        self.last_successful_post = utc_now_iso()
        self.successful_posts += 1
        self.increment("posts_successful")

        return True

    def _queue_post(self, path, payload):
        with self._queue_lock:
            self._queue.push(path, payload)

    def _post(self, path, payload, allow_queue=True):
        if not self.is_ready():
            self.logger.warning(
                "Client not configured. Check TITAN_OS_BASE_URL/TITAN_OS_URL and TITAN_OS_API_KEY."
            )
            self.last_failed_post = utc_now_iso()
            self.failed_posts += 1
            self.increment("posts_failed")
            return False

        try:
            return self._send_now(path, payload)

        except Exception as error:
            self.logger.error("POST failed for %s: %s", path, error)

            self.last_failed_post = utc_now_iso()
            self.failed_posts += 1
            self.increment("posts_failed")

            if allow_queue:
                self._queue_post(path, payload)
                self.logger.warning("Queued failed request: %s", path)

            if self.on_error:
                try:
                    self.on_error(self, error)
                except Exception as callback_error:
                    self.logger.error("on_error callback failed: %s", callback_error)

            return False

    def _retry_delay(self, attempts):
        delay = DEFAULT_RETRY_BASE_DELAY * (2 ** max(0, attempts - 1))
        return min(delay, DEFAULT_RETRY_MAX_DELAY)

    def _flush_queue_once(self):
        if not self.is_ready():
            return False

        with self._queue_lock:
            item = self._queue.pop()

        if not item:
            return False

        item["attempts"] = int(item.get("attempts", 0)) + 1

        try:
            self._send_now(item["path"], item["payload"])
            self.queue_flushes += 1
            self.increment("queue_flushes")
            self.logger.info("Flushed queued request: %s", item["path"])
            return True

        except Exception as error:
            self.logger.error("Queue flush failed: %s", error)

            self.last_failed_post = utc_now_iso()
            self.failed_posts += 1
            self.queue_retries += 1
            self.increment("posts_failed")
            self.increment("queue_retries")

            if item["attempts"] < DEFAULT_RETRY_MAX_ATTEMPTS:
                with self._queue_lock:
                    self._queue.push_front(item)

                time.sleep(self._retry_delay(item["attempts"]))
            else:
                self.queue_drops += 1
                self.increment("queue_drops")
                self.logger.error(
                    "Dropped queued request after %s attempts: %s",
                    item["attempts"],
                    item["path"],
                )
            return False

    def flush_queue(self, max_items=25):
        flushed = 0
        for _ in range(max_items):
            if not self._flush_queue_once():
                break
            flushed += 1
        return flushed

    def _queue_loop(self):
        while self._running:
            self._flush_queue_once()
            time.sleep(DEFAULT_QUEUE_FLUSH_INTERVAL)

    def register_service(self):
        payload = {
            "service_key": self.service_key,
            "name": self.name,
            "version": self.version,
            "category": self.category,
            "icon": self.icon,
            "route": self.route,
            "capabilities": self.capabilities,
            "operations": self.operations(),
            "registered_at": utc_now_iso(),
            **self.runtime_payload(),
        }

        ok = self._post("/api/register-service", payload)

        if ok:
            self.logger.info("Registered service: %s", self.service_key)
        else:
            self.logger.error("Failed to register service: %s", self.service_key)

        return ok

    def heartbeat(self, status="online", current_state="Running"):
        if self.on_heartbeat:
            try:
                self.on_heartbeat(self)
            except Exception as error:
                self._handle_callback_error("on_heartbeat", error)

        payload = {
            "service_key": self.service_key,
            "status": status,
            "current_state": current_state,
            "version": self.version,
            "last_heartbeat": utc_now_iso(),
            **self.runtime_payload(),
        }

        ok = self._post("/api/heartbeat", payload, allow_queue=False)

        if ok:
            self.heartbeats_sent += 1
            self.increment("heartbeats_sent")

        return ok

    def status(self, status="healthy", current_state="Running", metrics=None):
        merged_metrics = self.metrics_snapshot()
        if metrics:
            merged_metrics["application"] = metrics

        payload = {
            "service_key": self.service_key,
            "name": self.name,
            "status": status,
            "current_state": current_state,
            "version": self.version,
            "updated_at": utc_now_iso(),
            "metrics": merged_metrics,
            **self.runtime_payload(),
        }

        return self._post("/api/status", payload)

    def event(self, title, message=None, level="info"):
        if level == "warning":
            self.increment("warnings")
        if level == "error":
            self.increment("errors")

        payload = {
            "service_key": self.service_key,
            "title": title,
            "message": message or title,
            "level": level,
            "source": self.name,
            "created_at": utc_now_iso(),
            **self.runtime_payload(),
        }

        ok = self._post("/api/event", payload)

        if ok:
            self.events_sent += 1
            self.increment("events_sent")

        return ok

    def metric(self, name, value):
        self.set_gauge(name, value)
        return self.metrics({name: value})

    def metrics(self, metrics=None):
        if metrics:
            self.merge_metrics(metrics)

        payload = {
            "service_key": self.service_key,
            "metrics": self.metrics_snapshot(),
            "updated_at": utc_now_iso(),
            **self.runtime_payload(),
        }

        ok = self._post("/api/metrics", payload)

        if ok:
            self.metrics_sent += 1
            self.increment("metrics_sent")

        return ok

    def warning(self, title, message=None):
        return self.event(title, message, level="warning")

    def error(self, title, message=None):
        return self.event(title, message, level="error")

    def log(self, title, message=None):
        return self.event(title, message, level="info")

    def _heartbeat_loop(self):
        while self._running:
            self.heartbeat(status="online", current_state="Running")
            time.sleep(self.heartbeat_interval)

    def start(self):
        if not self.enabled:
            self.logger.warning("SDK disabled.")
            return False

        if self._running:
            self.logger.info("Service already running: %s", self.service_key)
            return True

        self.logger.info("Starting service: %s", self.service_key)
        self.logger.info("Config report: %s", self.config_report())

        if not self.is_ready():
            self.logger.error(
                "Not ready. Missing TITAN_OS_BASE_URL/TITAN_OS_URL or TITAN_OS_API_KEY."
            )
            return False

        self._running = True
        self.start_count += 1
        self.increment("starts")

        if self.on_start:
            try:
                self.on_start(self)
            except Exception as error:
                self._handle_callback_error("on_start", error)

        self.register_service()
        self.status(status="starting", current_state="Starting")
        self.event("Service started", f"{self.name} started successfully.")
        self.heartbeat(status="online", current_state="Running")

        self._heartbeat_thread = threading.Thread(
            target=self._heartbeat_loop,
            daemon=True,
        )
        self._heartbeat_thread.start()

        self._queue_thread = threading.Thread(
            target=self._queue_loop,
            daemon=True,
        )
        self._queue_thread.start()

        self.status(status="healthy", current_state="Running")

        self.logger.info("Service running: %s", self.service_key)

        return True

    def stop(self):
        if not self._running:
            self.logger.info("Service already stopped: %s", self.service_key)
            return True

        self.status(status="stopping", current_state="Stopping")
        self.event("Service stopping", f"{self.name} is shutting down.")
        self.metrics()
        self.flush_queue(max_items=25)

        if self.on_stop:
            try:
                self.on_stop(self)
            except Exception as error:
                self._handle_callback_error("on_stop", error)

        self._running = False
        self.stop_count += 1
        self.increment("stops")

        self.heartbeat(status="offline", current_state="Stopped")
        self.status(status="offline", current_state="Stopped")
        self.event("Service stopped", f"{self.name} stopped.")
        self.flush_queue(max_items=25)

        self.logger.info("Service stopped: %s", self.service_key)

        return True
