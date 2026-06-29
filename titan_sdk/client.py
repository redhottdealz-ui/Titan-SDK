import os
import socket
import time
import threading
from collections import deque
from datetime import datetime, timezone

import requests

from .constants import (
    DEFAULT_HEARTBEAT_INTERVAL,
    DEFAULT_QUEUE_FLUSH_INTERVAL,
    DEFAULT_QUEUE_RETRY_DELAY,
    DEFAULT_TIMEOUT,
    SDK_NAME,
)
from .version import SDK_VERSION


def utc_now_iso():
    return datetime.now(timezone.utc).isoformat()


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

        self.hostname = socket.gethostname()
        self.started_at = utc_now_iso()
        self.sdk_name = SDK_NAME
        self.sdk_version = SDK_VERSION

        self._running = False
        self._heartbeat_thread = None
        self._queue_thread = None
        self._queue = deque(maxlen=max_queue_size)
        self._queue_lock = threading.Lock()

    def uptime_seconds(self):
        try:
            started = datetime.fromisoformat(self.started_at)
            return int((datetime.now(timezone.utc) - started).total_seconds())
        except Exception:
            return 0

    def queue_size(self):
        with self._queue_lock:
            return len(self._queue)

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
            "health_message": "SDK reporting is active.",
        }

    def runtime_payload(self):
        return {
            "hostname": self.hostname,
            "started_at": self.started_at,
            "sdk_name": self.sdk_name,
            "sdk_version": self.sdk_version,
            "uptime_seconds": self.uptime_seconds(),
            "queue_size": self.queue_size(),
            **self.health_payload(),
        }

    def is_ready(self):
        return bool(self.enabled and self.base_url and self.api_key)

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
        return True

    def _queue_post(self, path, payload):
        with self._queue_lock:
            self._queue.append({
                "path": path,
                "payload": payload,
                "queued_at": utc_now_iso(),
            })

    def _post(self, path, payload, allow_queue=True):
        if not self.is_ready():
            print("[Titan SDK] Client not configured. Check TITAN_OS_BASE_URL/TITAN_OS_URL and TITAN_OS_API_KEY.")
            return False

        try:
            return self._send_now(path, payload)

        except Exception as error:
            print(f"[Titan SDK] POST failed for {path}: {error}")

            if allow_queue:
                self._queue_post(path, payload)
                print(f"[Titan SDK] Queued failed request: {path}")

            return False

    def _flush_queue_once(self):
        if not self.is_ready():
            return

        with self._queue_lock:
            if not self._queue:
                return

            item = self._queue.popleft()

        try:
            self._send_now(item["path"], item["payload"])
            print(f"[Titan SDK] Flushed queued request: {item['path']}")

        except Exception as error:
            print(f"[Titan SDK] Queue flush failed: {error}")

            with self._queue_lock:
                self._queue.appendleft(item)

            time.sleep(DEFAULT_QUEUE_RETRY_DELAY)

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
            "registered_at": utc_now_iso(),
            **self.runtime_payload(),
        }

        ok = self._post("/api/register-service", payload)

        if ok:
            print(f"[Titan SDK] Registered service: {self.service_key}")
        else:
            print(f"[Titan SDK] Failed to register service: {self.service_key}")

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

        return self._post("/api/heartbeat", payload, allow_queue=False)

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

        return self._post("/api/event", payload)

    def metric(self, name, value):
        return self.metrics({name: value})

    def metrics(self, metrics):
        payload = {
            "service_key": self.service_key,
            "metrics": metrics or {},
            "updated_at": utc_now_iso(),
            **self.runtime_payload(),
        }

        return self._post("/api/metrics", payload)

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
            print("[Titan SDK] Disabled.")
            return False

        if not self.is_ready():
            print("[Titan SDK] Not ready. Missing TITAN_OS_BASE_URL/TITAN_OS_URL or TITAN_OS_API_KEY.")
            return False

        if self._running:
            print(f"[Titan SDK] Service already running: {self.service_key}")
            return True

        print(f"[Titan SDK] Starting service: {self.service_key}")

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

        print(f"[Titan SDK] Service running: {self.service_key}")

        return True

    def stop(self):
        self._running = False

        self.status(status="offline", current_state="Stopped")
        self.event("Service stopped", f"{self.name} stopped.")

        print(f"[Titan SDK] Service stopped: {self.service_key}")
