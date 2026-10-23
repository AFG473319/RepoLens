import unittest
from datetime import datetime, timedelta, timezone

import cache
import scoring
from analyzer import analyze_commits
from dates import parse_iso_datetime


class TestParseIsoDatetime(unittest.TestCase):
    def test_z_suffix_becomes_utc(self):
        dt = parse_iso_datetime("2024-06-15T10:00:00Z")
        self.assertEqual(dt, datetime(2024, 6, 15, 10, 0, tzinfo=timezone.utc))

    def test_positive_offset_is_kept_not_converted(self):
        dt = parse_iso_datetime("2024-06-15T10:00:00+03:30")
        self.assertEqual(dt, datetime(2024, 6, 15, 6, 30, tzinfo=timezone.utc))
        self.assertEqual(dt.utcoffset(), timedelta(hours=3, minutes=30))

    def test_negative_offset_is_kept_not_converted(self):
        dt = parse_iso_datetime("2024-06-15T10:00:00-05:00")
        self.assertEqual(dt, datetime(2024, 6, 15, 15, 0, tzinfo=timezone.utc))
        self.assertEqual(dt.utcoffset(), timedelta(hours=-5))

    def test_naive_value_gets_utc(self):
        dt = parse_iso_datetime("2024-06-15T10:00:00")
        self.assertEqual(dt, datetime(2024, 6, 15, 10, 0, tzinfo=timezone.utc))
        self.assertEqual(dt.utcoffset(), timedelta(0))

    def test_date_only_gets_midnight_utc(self):
        dt = parse_iso_datetime("2024-06-15")
        self.assertEqual(dt, datetime(2024, 6, 15, 0, 0, tzinfo=timezone.utc))

    def test_invalid_strings_return_none(self):
        for value in ("not-a-date", "", "2024-13-45"):
            with self.subTest(value=value):
                self.assertIsNone(parse_iso_datetime(value))

    def test_non_strings_return_none(self):
        for value in (None, 123, {"date": "2024-06-15"}):
            with self.subTest(value=value):
                self.assertIsNone(parse_iso_datetime(value))


class TestModulesUseSharedHelper(unittest.TestCase):
    def test_scoring_days_since_uses_shared_helper(self):
        result = scoring._days_since(
            "2024-06-15", now=datetime(2024, 6, 25, tzinfo=timezone.utc)
        )
        self.assertEqual(result, 10)

    def test_analyzer_latest_commit_date_uses_shared_helper(self):
        commits = [
            # naive value treated as UTC (06:00); trailing "Z" equals 07:00 UTC
            {"commit": {"author": {"name": "A", "date": "2024-05-01T06:00:00"}}},
            {"commit": {"author": {"name": "B", "date": "2024-05-01T07:00:00Z"}}},
        ]
        result = analyze_commits(commits)
        self.assertEqual(result["latest_commit_date"], "2024-05-01T07:00:00Z")

    def test_cache_checks_uses_shared_helper(self):
        payload = {"fetched_at": "2024-06-15T12:00:00Z"}
        now = datetime(2024, 6, 15, 13, 0, tzinfo=timezone.utc)
        self.assertTrue(cache.is_cache_fresh(payload, ttl_seconds=3600, now=now))
        self.assertEqual(cache.cache_age_string(payload, now=now), "1 hour ago")


if __name__ == "__main__":
    unittest.main()
