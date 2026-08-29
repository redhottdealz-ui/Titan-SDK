import unittest
from unittest.mock import patch

from titan_sdk.client import TitanClient
from titan_sdk.constants import DEFAULT_RETRY_BASE_DELAY, DEFAULT_RETRY_MAX_DELAY
from titan_sdk.heartbeat import HEARTBEAT_PROTOCOL


class CommunicationsHealthFoundationTests(unittest.TestCase):
    def client(self, **kwargs):
        defaults = {
            "service_key": "test_service",
            "name": "Test Service",
            "version": "9.9.9",
            "base_url": "https://control-center.example",
            "api_key": "test-key",
        }
        defaults.update(kwargs)
        return TitanClient(**defaults)

    def test_component_health_contract_is_backward_compatible_and_preserves_metadata(self):
        client = self.client(capabilities=["discord"])
        client.set_heartbeat_component(
            "discord_gateway",
            status="offline",
            message="Gateway session unavailable.",
            critical=True,
            dependency="discord",
            ready=False,
        )

        payload = client.unified_heartbeat_payload(diagnostics={})
        component = payload["components"]["discord_gateway"]

        self.assertEqual(payload["protocol"], HEARTBEAT_PROTOCOL)
        self.assertEqual(component["status"], "error")
        self.assertEqual(component["message"], "Gateway session unavailable.")
        self.assertTrue(component["critical"])
        self.assertEqual(component["dependency"], "discord")
        self.assertFalse(component["ready"])
        self.assertIn("updated_at", component)

    def test_heartbeat_transport_failure_is_ephemeral_and_never_queued(self):
        client = self.client()
        with patch.object(client, "_send_now", side_effect=RuntimeError("control center unavailable")):
            self.assertFalse(client.heartbeat(status="healthy", current_state="Running"))

        self.assertEqual(client.queue_size(), 0)
        self.assertEqual(client.failed_posts, 1)

    def test_unified_heartbeat_transport_failure_is_ephemeral_and_never_queued(self):
        client = self.client()
        with patch.object(client, "_send_now", side_effect=RuntimeError("control center unavailable")):
            self.assertFalse(client.unified_heartbeat(status="healthy", current_state="Running", diagnostics={}))

        self.assertEqual(client.queue_size(), 0)
        self.assertEqual(client.failed_posts, 1)

    def test_capability_fingerprint_is_deterministic_and_order_insensitive(self):
        first = self.client(capabilities=["discord", "scheduler"])
        second = self.client(capabilities=["scheduler", "discord"])

        self.assertTrue(hasattr(first, "capability_fingerprint"))
        self.assertEqual(first.capability_fingerprint(), second.capability_fingerprint())
        self.assertEqual(first.capability_fingerprint(), first.capability_fingerprint())

    def test_retry_delay_has_bounded_jitter_to_avoid_fleet_retry_storms(self):
        client = self.client()
        attempts = 2
        delays = [client._retry_delay(attempts) for _ in range(12)]

        self.assertGreater(len(set(delays)), 1, "retry delay must include jitter")
        deterministic_delay = min(
            DEFAULT_RETRY_BASE_DELAY * (2 ** max(0, attempts - 1)),
            DEFAULT_RETRY_MAX_DELAY,
        )
        lower = deterministic_delay * 0.8
        upper = min(deterministic_delay * 1.2, DEFAULT_RETRY_MAX_DELAY)
        self.assertTrue(all(lower <= delay <= upper for delay in delays))


if __name__ == "__main__":
    unittest.main()
