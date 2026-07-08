"""Titan SDK command and execution telemetry helpers."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict

from .runtime import utc_now_iso


@dataclass
class CommandTelemetry:
    command_name: str
    service_key: str = ""
    guild_id: str = ""
    user_id: str = ""
    status: str = "started"
    started_at: str = field(default_factory=utc_now_iso)
    finished_at: str = ""
    duration_ms: int = 0
    error: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    _started_epoch: float = field(default_factory=time.time, repr=False)

    def finish(self, status="success", error=""):
        self.status = status
        self.finished_at = utc_now_iso()
        self.duration_ms = int((time.time() - self._started_epoch) * 1000)
        self.error = str(error or "")
        return self

    def to_dict(self):
        return {
            "command_name": self.command_name,
            "service_key": self.service_key,
            "guild_id": self.guild_id,
            "user_id": self.user_id,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_ms": self.duration_ms,
            "error": self.error,
            "metadata": self.metadata,
        }
