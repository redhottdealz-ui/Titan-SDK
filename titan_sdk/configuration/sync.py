from __future__ import annotations

from threading import RLock
from typing import Any, Callable, Dict, Optional

from .models import ConfigurationApplyResult, ConfigurationSnapshot

ApplyHandler = Callable[[ConfigurationSnapshot], ConfigurationApplyResult]


class HotReloadRegistry:
    def __init__(self) -> None:
        self._handlers: Dict[str, ApplyHandler] = {}
        self._lock = RLock()

    def register(self, product_key: str, handler: ApplyHandler) -> None:
        with self._lock:
            self._handlers[str(product_key).strip().lower()] = handler

    def apply(self, snapshot: ConfigurationSnapshot) -> ConfigurationApplyResult:
        handler: Optional[ApplyHandler] = self._handlers.get(snapshot.product_key.strip().lower())
        if handler is None:
            return ConfigurationApplyResult(status="pending_restart", applied_version=snapshot.version, message="No hot-reload handler is registered.")
        return handler(snapshot)


hot_reload_registry = HotReloadRegistry()
