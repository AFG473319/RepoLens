import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import cache


class TestCache(unittest.TestCase):
    def test_sanitize_replaces_unsafe_characters(self):
        self.assertEqual(cache._sanitize("owner/name"), "owner_name")

    def test_cache_path_uses_configured_directory(self):
        path = cache._cache_path("owner", "repo", Path("cache"))
        self.assertEqual(path, Path("cache/owner_repo.json"))

    def test_valid_payload(self):
        payload = self._payload()
        self.assertTrue(cache.is_cache_valid(payload))

    def test_invalid_payload_is_rejected(self):
        payload = self._payload()
        payload["version"] = 999
        self.assertFalse(cache.is_cache_valid(payload))

    def test_invalid_timestamp_is_not_fresh(self):
        payload = self._payload()
        payload["fetched_at"] = "invalid"
        self.assertFalse(cache.is_cache_fresh(payload))

    def test_freshness(self):
        now = datetime.now(timezone.utc)
        payload = self._payload(now - timedelta(hours=1))
        self.assertTrue(cache.is_cache_fresh(payload, now=now))
        self.assertFalse(cache.is_cache_fresh(payload, ttl_seconds=60, now=now))

    def test_load_cache_ignores_invalid_json(self):
        with tempfile.TemporaryDirectory() as directory:
            cache_dir = Path(directory)
            (cache_dir / "owner_repo.json").write_text("invalid", encoding="utf-8")
            self.assertIsNone(cache.load_cache("owner", "repo", cache_dir=cache_dir))

    def test_save_and_load_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            cache_dir = Path(directory)
            with patch.object(cache, "REGISTRY_PATH", cache_dir / "registry.json"):
                cache.save_cache("owner", "repo", self._analysis(), self._scores(), cache_dir=cache_dir)
                loaded = cache.load_cache("owner", "repo", cache_dir=cache_dir)
            self.assertEqual(loaded["owner"], "owner")
            self.assertEqual(loaded["analysis"], self._analysis())

    def test_clear_all_cache_removes_json_files(self):
        with tempfile.TemporaryDirectory() as directory:
            cache_dir = Path(directory)
            (cache_dir / "one.json").write_text("{}", encoding="utf-8")
            with patch.object(cache, "CACHE_DIR", cache_dir), patch.object(cache, "REGISTRY_PATH", cache_dir / "registry.json"):
                self.assertEqual(cache.clear_all_cache(), 1)
            self.assertFalse((cache_dir / "one.json").exists())

    @staticmethod
    def _analysis():
        return {"repo": {}, "commits": {}, "contributors": {}, "languages": {}, "issues": {}, "approximate": False, "truncated_endpoints": []}

    @staticmethod
    def _scores():
        return {"health_score": 0, "activity_score": 0, "community_score": 0, "maintainability_score": 0, "grade": "F"}

    def _payload(self, fetched_at=None):
        return {"version": cache.CACHE_VERSION, "owner": "owner", "repo": "repo", "fetched_at": (fetched_at or datetime.now(timezone.utc)).isoformat(), "analysis": self._analysis(), "scores": self._scores()}


if __name__ == "__main__":
    unittest.main()
