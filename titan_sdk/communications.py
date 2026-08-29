"""Additive communications and health behavior for Titan SDK canary adoption.

This module intentionally subclasses the existing TitanClient instead of changing
its established runtime contracts. Services can opt in during the controlled
fleet migration while legacy TitanClient behavior remains untouched.
"""
from __future__ import annotations

import hashlib
import json
import random

from .client import TitanClient
from .constants import DEFAULT_RETRY_BASE_DELAY, DEFAULT_RETRY_MAX_DELAY
from .capabilities import build_capability_payload


class TitanCommunicationsClient(TitanClient):
    """Backward-compatible TitanClient with Phase 1A communications improvements."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_synced_capability_fingerprint = None

    def capability_fingerprint(self) -> str:
        """Return a deterministic, order-insensitive capability fingerprint."""
        payload = build_capability_payload(sorted(self.capabilities), include_defaults=False)
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def sync_capabilities_if_changed(self) -> bool:
        """Publish capability registration only when effective capability state changed.

        A failed registration never advances the local synchronization marker, so
        the next call retries the same capability contract instead of suppressing it.
        """
        fingerprint = self.capability_fingerprint()
        if fingerprint == self._last_synced_capability_fingerprint:
            return False

        synced = bool(super().register_service())
        if synced:
            self._last_synced_capability_fingerprint = fingerprint
        return synced

    def _retry_delay(self, attempts):
        """Preserve exponential backoff while adding bounded fleet-safe jitter."""
        deterministic_delay = min(
            DEFAULT_RETRY_BASE_DELAY * (2 ** max(0, attempts - 1)),
            DEFAULT_RETRY_MAX_DELAY,
        )
        lower = deterministic_delay * 0.8
        upper = min(deterministic_delay * 1.2, DEFAULT_RETRY_MAX_DELAY)
        return random.uniform(lower, upper)
