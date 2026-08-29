import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import settings


class TestSettings(unittest.TestCase):
    def test_default_settings_without_environment(self):
        with patch.dict(os.environ, {}, clear=True):
            values = settings._default_settings()
        self.assertEqual(values["github_api_key"], "")
        self.assertEqual(values["cache_directory"], str(settings.DEFAULT_CACHE_DIRECTORY))

    def test_load_settings_missing_file_uses_defaults(self):
        with patch.object(settings, "SETTINGS_PATH", Path("missing-settings.json")):
            with patch.object(settings, "_default_settings", return_value={"github_api_key": "env", "cache_directory": "cache"}):
                self.assertEqual(settings.load_settings(), {"github_api_key": "env", "cache_directory": "cache"})

    def test_save_and_load_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            values = {"github_api_key": " secret ", "cache_directory": " /tmp/cache "}
            with patch.object(settings, "SETTINGS_PATH", path):
                settings.save_settings(values)
                self.assertEqual(settings.load_settings(), {"github_api_key": "secret", "cache_directory": "/tmp/cache"})

    def test_load_settings_ignores_malformed_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text("not json", encoding="utf-8")
            with patch.object(settings, "SETTINGS_PATH", path):
                with patch.object(settings, "_default_settings", return_value={"github_api_key": "env", "cache_directory": "cache"}):
                    self.assertEqual(settings.load_settings(), {"github_api_key": "env", "cache_directory": "cache"})

    def test_save_settings_rejects_invalid_values(self):
        with self.assertRaises(TypeError):
            settings.save_settings(None)
        with self.assertRaises(TypeError):
            settings.save_settings({"github_api_key": None, "cache_directory": "cache"})

    def test_save_settings_uses_default_for_blank_cache_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            with patch.object(settings, "SETTINGS_PATH", path):
                settings.save_settings({"github_api_key": "key", "cache_directory": "   "})
                saved = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(saved["cache_directory"], str(settings.DEFAULT_CACHE_DIRECTORY))

    def test_apply_settings_updates_environment_and_cache_directory(self):
        import cache
        with patch.dict(os.environ, {}, clear=True):
            settings.apply_settings({"github_api_key": "secret", "cache_directory": "cache"})
            self.assertEqual(os.environ["GITHUB_API_KEY"], "secret")
            self.assertEqual(os.environ["REPOLENS_CACHE_DIR"], "cache")
            self.assertEqual(cache.CACHE_DIR, Path("cache"))


if __name__ == "__main__":
    unittest.main()
