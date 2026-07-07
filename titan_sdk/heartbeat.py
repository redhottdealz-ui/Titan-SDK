"""Titan SDK Unified Heartbeat Framework.

This module defines the shared heartbeat payload used by Titan services.
It is intentionally lightweight and dependency-free so bots and workers can
report richer health without adding runtime cost.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional

from .runtime import utc_now_iso
from .version import SDK_VERSION


HEARTBEAT_PROTOCOL = "titan_sdk_unified_heartbeat_v1"


def normalize_status(value: Optional[str], default: str = "unknown") -> str:
    raw = str(value or default).strip().lower().replace(" ", "_")
    if raw in {"ok", "online", "ready", "healthy", "success", "synced", "current", "updated"}:
        return "healthy"
    if raw in {"warn", "warning", "stale", "degraded", "using_cache", "bundled_defaults"}:
        return "warning"
    if raw in {"err", "error", "failed", "critical", "offline"}:
        return "error"
    return raw or default


def component_status(status: str = "unknown", message: str = "", **fields: Any) -> Dict[str, Any]:
    payload = {
        "status": normalize_status(status),
        "message": str(message or ""),
        "updated_at": utc_now_iso(),
    }
    payload.update({key: value for key, value in fields.items() if value is not None})
    return payload


@dataclass
class TitanHeartbeat:
    service_key: str
    service_name: str
    service_version: str
    status: str = "healthy"
    current_state: str = "Running"
    sdk_version: str = SDK_VERSION
    protocol: str = HEARTBEAT_PROTOCOL
    generated_at: str = field(default_factory=utc_now_iso)
    components: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    compatibility: Dict[str, Any] = field(default_factory=dict)
    diagnostics: Dict[str, Any] = field(default_factory=dict)
    last_error: str = ""

    def add_component(self, name: str, status: str = "unknown", message: str = "", **fields: Any) -> "TitanHeartbeat":
        self.components[str(name)] = component_status(status=status, message=message, **fields)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return {
            "protocol": self.protocol,
            "generated_at": self.generated_at,
            "service": {
                "key": self.service_key,
                "name": self.service_name,
                "version": self.service_version,
                "sdk_version": self.sdk_version,
            },
            "status": normalize_status(self.status),
            "current_state": self.current_state,
            "components": self.components,
            "metrics": self.metrics,
            "compatibility": self.compatibility,
            "diagnostics": self.diagnostics,
            "last_error": self.last_error or "",
        }


def build_unified_heartbeat(
    *,
    service_key: str,
    service_name: str,
    service_version: str,
    status: str = "healthy",
    current_state: str = "Running",
    components: Optional[Mapping[str, Mapping[str, Any]]] = None,
    metrics: Optional[Mapping[str, Any]] = None,
    compatibility: Optional[Mapping[str, Any]] = None,
    diagnostics: Optional[Mapping[str, Any]] = None,
    last_error: str = "",
) -> Dict[str, Any]:
    heartbeat = TitanHeartbeat(
        service_key=service_key,
        service_name=service_name,
        service_version=service_version,
        status=status,
        current_state=current_state,
        metrics=dict(metrics or {}),
        compatibility=dict(compatibility or {}),
        diagnostics=dict(diagnostics or {}),
        last_error=last_error or "",
    )
    for name, payload in dict(components or {}).items():
        if isinstance(payload, Mapping):
            copied = dict(payload)
            component_status_value = copied.pop("status", "unknown")
            message = copied.pop("message", "")
            heartbeat.add_component(name, status=component_status_value, message=message, **copied)
    return heartbeat.to_dict()
