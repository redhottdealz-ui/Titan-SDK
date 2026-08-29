"""Additive communications and health behavior for Titan SDK canary adoption.

This module intentionally subclasses the existing TitanClient instead of changing
its established runtime contracts. Services can opt in during the controlled
fleet migration while legacy TitanClient behavior remains untouched.
"""
from __future__ import annotations

import hashlib
import json
import os
import random
import time
from pathlib import Path

from .client import TitanClient
from .constants import DEFAULT_RETRY_BASE_DELAY, DEFAULT_RETRY_MAX_ATTEMPTS, DEFAULT_RETRY_MAX_DELAY
from .capabilities import build_capability_payload
from .runtime import utc_now_iso


DEFAULT_OUTAGE_REPROBE_INTERVAL = 30.0


class TitanCommunicationsClient(TitanClient):
    """Backward-compatible TitanClient with Phase 1A communications improvements."""

    def __init__(self, *args, durable_delivery_path=None, outage_reprobe_interval=DEFAULT_OUTAGE_REPROBE_INTERVAL, **kwargs):
        self._durable_delivery_path = Path(durable_delivery_path) if durable_delivery_path else None
        self._outage_reprobe_interval = max(0.0, float(outage_reprobe_interval))
        super().__init__(*args, **kwargs)
        self._last_synced_capability_fingerprint = None
        self._control_center_outage = False
        self._control_center_outage_observed_at = None
        self._restore_durable_deliveries()

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

    def control_center_outage_active(self) -> bool:
        """Return whether the communications client has observed a transport outage."""
        return bool(self._control_center_outage)

    def _mark_control_center_outage(self):
        self._control_center_outage = True
        self._control_center_outage_observed_at = time.monotonic()

    def _clear_control_center_outage(self):
        self._control_center_outage = False
        self._control_center_outage_observed_at = None

    def _ephemeral_transport_suppressed(self) -> bool:
        if not self._control_center_outage:
            return False
        if self._control_center_outage_observed_at is None:
            return False
        elapsed = time.monotonic() - self._control_center_outage_observed_at
        return elapsed < self._outage_reprobe_interval

    def _load_durable_deliveries(self):
        if self._durable_delivery_path is None:
            return []
        try:
            value = json.loads(self._durable_delivery_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return []
        if not isinstance(value, list):
            return []
        return [item for item in value if isinstance(item, dict) and item.get("path")]

    def _save_durable_deliveries(self, rows):
        if self._durable_delivery_path is None:
            return
        self._durable_delivery_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._durable_delivery_path.with_suffix(self._durable_delivery_path.suffix + ".tmp")
        temporary.write_text(json.dumps(rows, indent=2, sort_keys=True), encoding="utf-8")
        os.replace(temporary, self._durable_delivery_path)

    def _restore_durable_deliveries(self):
        for item in self._load_durable_deliveries():
            self._queue_post(item["path"], item.get("payload") or {})

    def _persist_important_delivery(self, path, payload):
        if self._durable_delivery_path is None:
            return
        rows = self._load_durable_deliveries()
        rows.append({"path": path, "payload": payload})
        self._save_durable_deliveries(rows)

    def _remove_durable_delivery(self, path, payload):
        if self._durable_delivery_path is None:
            return
        rows = self._load_durable_deliveries()
        for index, item in enumerate(rows):
            if item.get("path") == path and item.get("payload") == payload:
                del rows[index]
                self._save_durable_deliveries(rows)
                return

    def durable_delivery_count(self) -> int:
        return len(self._load_durable_deliveries())

    def deliver(self, path, payload, *, delivery_class="important") -> bool:
        """Deliver an explicitly classified Control Center request.

        ``ephemeral`` traffic is never queued and is temporarily suppressed after
        an observed outage, then one request is allowed to reprobe after the bounded
        cooldown. ``reconstructable`` traffic is retried only when its caller
        explicitly reconstructs current state. ``important`` traffic is attempted
        and durably queued on failure. ``probe`` always attempts transport and
        clears outage state on success.
        """
        delivery_class = str(delivery_class or "important").strip().lower()
        if delivery_class not in {"ephemeral", "reconstructable", "important", "probe"}:
            raise ValueError("delivery_class must be ephemeral, reconstructable, important, or probe")

        if delivery_class == "ephemeral" and self._ephemeral_transport_suppressed():
            return False

        if not self.is_ready():
            return False

        try:
            sent = bool(self._send_now(path, payload))
        except Exception as error:
            self._mark_control_center_outage()
            self.last_failed_post = utc_now_iso()
            self.failed_posts += 1
            self.increment("posts_failed")
            if delivery_class == "important":
                self._persist_important_delivery(path, payload)
                self._queue_post(path, payload)
            if self.on_error:
                try:
                    self.on_error(self, error)
                except Exception as callback_error:
                    self.logger.error("on_error callback failed: %s", callback_error)
            return False

        if sent:
            self._clear_control_center_outage()
        return sent

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
            self._remove_durable_delivery(item["path"], item["payload"])
            self._clear_control_center_outage()
            self.queue_flushes += 1
            self.increment("queue_flushes")
            self.logger.info("Flushed queued request: %s", item["path"])
            return True
        except Exception as error:
            self._mark_control_center_outage()
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
                self._remove_durable_delivery(item["path"], item["payload"])
                self.queue_drops += 1
                self.increment("queue_drops")
                self.logger.error("Dropped queued request after %s attempts: %s", item["attempts"], item["path"])
            return False

    def _retry_delay(self, attempts):
        """Preserve exponential backoff while adding bounded fleet-safe jitter."""
        deterministic_delay = min(
            DEFAULT_RETRY_BASE_DELAY * (2 ** max(0, attempts - 1)),
            DEFAULT_RETRY_MAX_DELAY,
        )
        lower = deterministic_delay * 0.8
        upper = min(deterministic_delay * 1.2, DEFAULT_RETRY_MAX_DELAY)
        return random.uniform(lower, upper)
