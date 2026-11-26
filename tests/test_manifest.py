"""Unit tests for Home Assistant and HACS manifests."""

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# Bump this together with the manifest, pyproject.toml and the changelog (RELEASING.md).
EXPECTED_VERSION = "3.0.1"


class TestManifests(unittest.TestCase):
    """Test Home Assistant and HACS manifests."""

    def test_custom_components_manifest(self) -> None:
        """Validate manifest.json fields."""
        manifest_path = Path("custom_components/welock_ble/manifest.json")
        self.assertTrue(
            manifest_path.exists(), "custom_components/welock_ble/manifest.json must exist"
        )

        with manifest_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data.get("domain"), "welock_ble")
        self.assertEqual(data.get("name"), "WeLock Smart Lock BLE")
        self.assertTrue(data.get("config_flow"))
        self.assertIn("@Ebenhoeh80", data.get("codeowners", []))
        self.assertEqual(data.get("iot_class"), "local_polling")
        self.assertRegex(data.get("version", ""), r"^\d+\.\d+\.\d+(-rc\.\d+)?$")
        self.assertIn("bleak-retry-connector>=3.1.0", data.get("requirements", []))
        self.assertIn("bluetooth_adapters", data.get("dependencies", []))
        self.assertTrue(any(m.get("local_name") == "WeLock*" for m in data.get("bluetooth", [])))

    def test_versions_agree(self) -> None:
        """Manifest, pyproject and the expected release version must be the same."""
        manifest = json.loads(
            (ROOT / "custom_components/welock_ble/manifest.json").read_text(encoding="utf-8")
        )
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        match = re.search(r'^version = "([^"]+)"$', pyproject, re.MULTILINE)
        self.assertIsNotNone(match, "pyproject.toml must declare a project version")
        assert match is not None  # for the type checker
        self.assertEqual(match.group(1), EXPECTED_VERSION)
        self.assertEqual(manifest.get("version"), EXPECTED_VERSION)

    def test_changelog_has_section_for_this_version(self) -> None:
        """A release without a changelog section would publish empty release notes."""
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        heading = re.compile(
            rf"^## \[{re.escape(EXPECTED_VERSION)}\] - \d{{4}}-\d{{2}}-\d{{2}}\s*$",
            re.MULTILINE,
        )
        found = heading.search(changelog)
        self.assertIsNotNone(found, f"CHANGELOG.md needs a section for {EXPECTED_VERSION}")
        assert found is not None  # for the type checker
        rest = changelog[found.end() :]
        next_heading = re.search(r"^## ", rest, re.MULTILINE)
        section = rest[: next_heading.start()] if next_heading else rest
        self.assertTrue(section.strip(), f"The {EXPECTED_VERSION} section must not be empty")

    def test_hacs_manifest(self) -> None:
        """Validate hacs.json fields."""
        hacs_path = Path("hacs.json")
        self.assertTrue(hacs_path.exists(), "hacs.json must exist")

        with hacs_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data.get("name"), "WeLock Smart Lock BLE")
        self.assertTrue(data.get("render_readme"))
        self.assertEqual(data.get("homeassistant"), "2025.7.0")


if __name__ == "__main__":
    unittest.main()
