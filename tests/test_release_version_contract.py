import pathlib
import re
import unittest

from titan_sdk.version import SDK_VERSION


class ReleaseVersionContractTests(unittest.TestCase):
    def test_runtime_and_package_metadata_match_v1_9_1(self):
        pyproject = pathlib.Path(__file__).resolve().parents[1] / "pyproject.toml"
        text = pyproject.read_text(encoding="utf-8")
        match = re.search(r'^version\s*=\s*"([^"]+)"$', text, re.MULTILINE)
        self.assertIsNotNone(match, "pyproject.toml must declare the package version")
        self.assertEqual(SDK_VERSION, "1.9.1")
        self.assertEqual(match.group(1), SDK_VERSION)


if __name__ == "__main__":
    unittest.main()
