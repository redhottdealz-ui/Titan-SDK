import os
import platform
import sys
import threading
from typing import Any, Callable, Dict, Optional

from .runtime import utc_now_iso


class DiagnosticsRegistry:
    def __init__(self):
        self._providers = []
        self._static: Dict[str, Any] = {}

    def add(self, provider: Callable, name: Optional[str] = None):
        self._providers.append((name or getattr(provider, "__name__", "provider"), provider))
        return provider

    def set_static(self, key, value):
        self._static[key] = value
        return value

    def collect(self, client=None):
        diagnostics = dict(self._static)
        for name, provider in self._providers:
            try:
                value = provider(client) if client is not None else provider()
                if isinstance(value, dict):
                    diagnostics.update(value)
                else:
                    diagnostics[name] = value
            except Exception as error:
                diagnostics[f"{name}_error"] = str(error)
        return diagnostics


def build_diagnostics(client):
    return {
        "generated_at": utc_now_iso(),
        "service_key": getattr(client, "service_key", "unknown"),
        "service_name": getattr(client, "name", "unknown"),
        "service_type": getattr(client, "service_type", "service"),
        "application_version": getattr(client, "version", "unknown"),
        "sdk_name": getattr(client, "sdk_name", "titan-sdk"),
        "sdk_version": getattr(client, "sdk_version", "unknown"),
        "hostname": getattr(client, "hostname", "unknown"),
        "pid": os.getpid(),
        "python_version": platform.python_version(),
        "python_executable": sys.executable,
        "platform": platform.platform(),
        "system": platform.system(),
        "machine": platform.machine(),
        "thread_count": threading.active_count(),
        "base_url_configured": bool(getattr(client, "base_url", "")),
        "api_key_configured": bool(getattr(client, "api_key", "")),
        "queue_size": client.queue_size() if hasattr(client, "queue_size") else 0,
        "uptime_seconds": client.uptime_seconds() if hasattr(client, "uptime_seconds") else 0,
        "repository": getattr(client, "repository", ""),
        "environment": getattr(client, "environment", ""),
        "deployment": getattr(client, "deployment", ""),
    }
