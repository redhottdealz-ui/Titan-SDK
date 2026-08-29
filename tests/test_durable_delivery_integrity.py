import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import mock_open, patch

from titan_sdk import TitanCommunicationsClient


class DurableDeliveryIntegrityTests(unittest.TestCase):
    def client(self, durable_path):
        return TitanCommunicationsClient(
            service_key="test_service",
            name="Test Service",
            version="9.9.9",
            base_url="https://control-center.example",
            api_key="test-key",
            durable_delivery_path=durable_path,
        )

    def test_durable_write_flushes_and_fsyncs_before_atomic_replace(self):
        with tempfile.TemporaryDirectory() as directory:
            durable_path = Path(directory) / "important-deliveries.json"
            client = self.client(durable_path)
            handle = mock_open()
            with patch("pathlib.Path.open", handle), patch("titan_sdk.communications.os.fsync") as fsync, patch(
                "titan_sdk.communications.os.replace"
            ) as replace:
                client._save_durable_deliveries([{"path": "/api/workflow-handoff", "payload": {"handoff_id": "h-1"}}])

            file_handle = handle()
            file_handle.flush.assert_called_once_with()
            fsync.assert_called_once_with(file_handle.fileno())
            replace.assert_called_once()

    def test_non_json_serializable_important_payload_fails_closed_without_queueing(self):
        with tempfile.TemporaryDirectory() as directory:
            durable_path = Path(directory) / "important-deliveries.json"
            client = self.client(durable_path)
            payload = {"handoff_id": "h-1", "unsupported": object()}
            with patch.object(client, "_send_now", side_effect=RuntimeError("control center unavailable")):
                self.assertFalse(client.deliver("/api/workflow-handoff", payload, delivery_class="important"))

            self.assertEqual(client.queue_size(), 0)
            self.assertEqual(client.durable_delivery_count(), 0)
            self.assertTrue(client.control_center_outage_active())


if __name__ == "__main__":
    unittest.main()
