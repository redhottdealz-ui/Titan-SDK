import unittest
from unittest.mock import patch

from titan_sdk import TitanCommunicationsClient


class OutageRecoveryTests(unittest.TestCase):
    def client(self):
        return TitanCommunicationsClient(
            service_key="test_service",
            name="Test Service",
            version="9.9.9",
            base_url="https://control-center.example",
            api_key="test-key",
        )

    def test_ephemeral_suppression_is_bounded_and_eventually_reprobes(self):
        client = self.client()
        with patch("titan_sdk.communications.time.monotonic", side_effect=[100.0, 110.0, 131.0]), patch.object(
            client,
            "_send_now",
            side_effect=[RuntimeError("control center unavailable"), True],
        ) as send:
            self.assertFalse(client.deliver("/api/metrics", {"value": 1}, delivery_class="ephemeral"))
            self.assertFalse(client.deliver("/api/metrics", {"value": 2}, delivery_class="ephemeral"))
            self.assertTrue(client.deliver("/api/metrics", {"value": 3}, delivery_class="ephemeral"))

        self.assertEqual(send.call_count, 2)
        self.assertFalse(client.control_center_outage_active())

    def test_failed_queue_retry_sleeps_using_jittered_retry_delay(self):
        client = self.client()
        client._queue_post("/api/workflow-handoff", {"handoff_id": "h-1"})
        with patch.object(client, "_send_now", side_effect=RuntimeError("still unavailable")), patch.object(
            client, "_retry_delay", return_value=7.25
        ) as retry_delay, patch("titan_sdk.communications.time.sleep") as sleep:
            self.assertFalse(client._flush_queue_once())

        retry_delay.assert_called_once_with(1)
        sleep.assert_called_once_with(7.25)
        self.assertEqual(client.queue_size(), 1)


if __name__ == "__main__":
    unittest.main()
