import unittest
from unittest.mock import patch

from titan_sdk.communications import TitanCommunicationsClient


class OutageAwareCoreDeliveryTests(unittest.TestCase):
    def client(self, **kwargs):
        defaults = {
            "service_key": "test_service",
            "name": "Test Service",
            "version": "9.9.9",
            "base_url": "https://control-center.example",
            "api_key": "test-key",
            "outage_reprobe_interval": 60,
        }
        defaults.update(kwargs)
        return TitanCommunicationsClient(**defaults)

    def test_heartbeat_failure_marks_outage_and_suppresses_immediate_reprobe(self):
        client = self.client()
        with patch.object(client, "_send_now", side_effect=RuntimeError("control center unavailable")) as send:
            self.assertFalse(client.heartbeat(status="healthy", current_state="Running"))
            self.assertTrue(client.control_center_outage_active())
            self.assertFalse(client.heartbeat(status="healthy", current_state="Running"))
        self.assertEqual(send.call_count, 1)
        self.assertEqual(client.queue_size(), 0)

    def test_unified_heartbeat_failure_marks_outage_and_suppresses_immediate_reprobe(self):
        client = self.client()
        with patch.object(client, "_send_now", side_effect=RuntimeError("control center unavailable")) as send:
            self.assertFalse(client.unified_heartbeat(status="healthy", current_state="Running", diagnostics={}))
            self.assertTrue(client.control_center_outage_active())
            self.assertFalse(client.unified_heartbeat(status="healthy", current_state="Running", diagnostics={}))
        self.assertEqual(send.call_count, 1)
        self.assertEqual(client.queue_size(), 0)

    def test_failed_capability_sync_is_reconstructable_not_retry_queued(self):
        client = self.client(capabilities=["discord"])
        with patch.object(client, "_send_now", side_effect=RuntimeError("control center unavailable")):
            self.assertFalse(client.sync_capabilities_if_changed())
        self.assertTrue(client.control_center_outage_active())
        self.assertEqual(client.queue_size(), 0)

    def test_capability_sync_recovers_without_stale_queued_registration(self):
        client = self.client(capabilities=["discord"])
        with patch.object(client, "_send_now", side_effect=[RuntimeError("control center unavailable"), True, True]) as send:
            self.assertFalse(client.sync_capabilities_if_changed())
            self.assertTrue(client.deliver("/api/health-probe", {}, delivery_class="probe"))
            self.assertTrue(client.sync_capabilities_if_changed())
            self.assertFalse(client.sync_capabilities_if_changed())
        self.assertEqual(send.call_count, 3)
        self.assertEqual(client.queue_size(), 0)
        self.assertFalse(client.control_center_outage_active())


if __name__ == "__main__":
    unittest.main()
