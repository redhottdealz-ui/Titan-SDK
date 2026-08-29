import unittest


class PublicApiTests(unittest.TestCase):
    def test_communications_client_is_exported_from_package_root(self):
        import titan_sdk

        self.assertTrue(hasattr(titan_sdk, "TitanCommunicationsClient"))
        from titan_sdk import TitanCommunicationsClient

        self.assertEqual(TitanCommunicationsClient.__name__, "TitanCommunicationsClient")


if __name__ == "__main__":
    unittest.main()
