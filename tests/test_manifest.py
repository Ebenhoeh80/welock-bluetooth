"""Unit tests for Home Assistant and HACS manifests."""

import json
import unittest
from pathlib import Path


class TestManifests(unittest.TestCase):
    """Test Home Assistant and HACS manifests."""

    def test_custom_components_manifest(self) -> None:
        """Validate manifest.json fields."""
        manifest_path = Path("custom_components/welock/manifest.json")
        self.assertTrue(manifest_path.exists(), "custom_components/welock/manifest.json must exist")

        with manifest_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data.get("domain"), "welock")
        self.assertEqual(data.get("name"), "WeLock Smart Lock")
        self.assertTrue(data.get("config_flow"))
        self.assertIn("@Ebenhoeh80", data.get("codeowners", []))
        self.assertEqual(data.get("iot_class"), "cloud_polling")
        self.assertEqual(data.get("version"), "1.3.0")
        self.assertIn("aiohttp>=3.9.0", data.get("requirements", []))
        self.assertIn("bluetooth_adapters", data.get("dependencies", []))
        self.assertTrue(any(m.get("local_name") == "WeLock*" for m in data.get("bluetooth", [])))

    def test_hacs_manifest(self) -> None:
        """Validate hacs.json fields."""
        hacs_path = Path("hacs.json")
        self.assertTrue(hacs_path.exists(), "hacs.json must exist")

        with hacs_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data.get("name"), "WeLock Smart Lock")
        self.assertTrue(data.get("render_readme"))
        self.assertEqual(data.get("homeassistant"), "2024.11.0")


if __name__ == "__main__":
    unittest.main()
