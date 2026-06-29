import os
import time
import threading

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
    ):
        self.service_key = service_key
        self.name = name
        self.version = version
        self.category = category
        self.icon = icon
        self.route = route or f"/services/{service_key}"
        self.capabilities = capabilities or []

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
        self.sdk_name = SDK_NAME
        self.sdk_version = SDK_VERSION

        self.logger = build_logger(f"Titan SDK:{self.service_key}")

        self._running = False
        self._heartbeat_thread = None
        self._queue_thread = None
        self._queue_lock = threading.Lock()
        self._queue = RetryQueue(max_size=max_queue_size)

        self.last_successful_post = None
        self.last_failed_post = None
        self.successful_posts = 0
        self.failed_posts = 0
        self.events_sent = 0
        self.metrics_sent = 0
        self.heartbeats_sent = 0

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
        return build_diagnostics(self)

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

        return {
            "health_status": "healthy",
            "health_message": "Service is operating normally.",
        }

    def runtime_payload(self):
        return {
            "hostname": self.hostname,
            "started_at": self.started_at,
            "sdk_name": self.sdk_name,
            "sdk_version": self.sdk_version,
            "uptime_seconds": self.uptime_seconds(),
            "queue_size": self.queue_size(),
            "successful_posts": self.successful_posts,
            "failed_posts": self.failed_posts,
            "events_sent": self.events_sent,
            "metrics_sent": self.metrics_sent,
            "heartbeats_sent": self.heartbeats_sent,
            "last_successful_post": self.last_successful_post,
            "last_failed_post": self.last_failed_post,
            "operations": self.operations(),
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
            "operations_registered": len(self.operations()),
        }

    def _headers(self):
        return {
            "Content-Type": "application/json",
            "X-Titan-API-Key": self.api_key or "",
        }

    def _url(self, path):
        return f"{self.base_url}{path}"

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
            return False

        try:
            return self._send_now(path, payload)

        except Exception as error:
            self.logger.error("POST failed for %s: %s", path, error)

            self.last_failed_post = utc_now_iso()
            self.failed_posts += 1

            if allow_queue:
                self._queue_post(path, payload)
                self.logger.warning("Queued failed request: %s", path)

            return False

    def _retry_delay(self, attempts):
        delay = DEFAULT_RETRY_BASE_DELAY * (2 ** max(0, attempts - 1))
        return min(delay, DEFAULT_RETRY_MAX_DELAY)

    def _flush_queue_once(self):
        if not self.is_ready():
            return

        with self._queue_lock:
            item = self._queue.pop()

        if not item:
            return

        item["attempts"] = int(item.get("attempts", 0)) + 1

        try:
            self._send_now(item["path"], item["payload"])
            self.logger.info("Flushed queued request: %s", item["path"])

        except Exception as error:
            self.logger.error("Queue flush failed: %s", error)

            self.last_failed_post = utc_now_iso()
            self.failed_posts += 1

            if item["attempts"] < DEFAULT_RETRY_MAX_ATTEMPTS:
                with self._queue_lock:
                    self._queue.push_front(item)

                time.sleep(self._retry_delay(item["attempts"]))
            else:
                self.logger.error(
                    "Dropped queued request after %s attempts: %s",
                    item["attempts"],
                    item["path"],
                )

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

        return ok

    def status(self, status="healthy", current_state="Running", metrics=None):
        payload = {
            "service_key": self.service_key,
            "name": self.name,
            "status": status,
            "current_state": current_state,
            "version": self.version,
            "updated_at": utc_now_iso(),
            "metrics": metrics or {},
            **self.runtime_payload(),
        }

        return self._post("/api/status", payload)

    def event(self, title, message=None, level="info"):
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

        return ok

    def metric(self, name, value):
        return self.metrics({name: value})

    def metrics(self, metrics):
        payload = {
            "service_key": self.service_key,
            "metrics": metrics or {},
            "updated_at": utc_now_iso(),
            **self.runtime_payload(),
        }

        ok = self._post("/api/metrics", payload)

        if ok:
            self.metrics_sent += 1

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

        self._running = False

        self.status(status="offline", current_state="Stopped")
        self.event("Service stopped", f"{self.name} stopped.")

        self.logger.info("Service stopped: %s", self.service_key)

        return True
