import unittest
from datetime import datetime, timedelta, timezone

from scoring import (
    calculate_activity_score,
    calculate_community_score,
    calculate_maintainability_score,
    calculate_health_score,
    grade_score,
)


def _recent_date(days_ago: int = 1) -> str:
    """Return an ISO date string ``days_ago`` days before now."""
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _stale_date() -> str:
    """Return an ISO date string well outside the recency window."""
    dt = datetime.now(timezone.utc) - timedelta(days=365)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class TestCalculateActivityScore(unittest.TestCase):
    def test_zero_commits(self):
        result = calculate_activity_score({"total_commits": 0})
        self.assertAlmostEqual(result, 0.0)

    def test_small_number_of_commits(self):
        result = calculate_activity_score({"total_commits": 10})
        self.assertTrue(result > 0)
        self.assertTrue(result <= 100.0)

    def test_large_number_of_commits(self):
        result = calculate_activity_score({"total_commits": 10000})
        self.assertAlmostEqual(result, 80.0, places=1)

    def test_with_latest_commit_date(self):
        result = calculate_activity_score({
            "total_commits": 10,
            "latest_commit_date": _recent_date(),
        })
        self.assertTrue(result > 10)

    def test_without_latest_commit_date(self):
        result = calculate_activity_score({
            "total_commits": 10,
            "latest_commit_date": None,
        })
        self.assertLessEqual(result, 100.0)

    def test_score_capped_at_100(self):
        result = calculate_activity_score({
            "total_commits": 100000,
            "latest_commit_date": _recent_date(),
        })
        self.assertLessEqual(result, 100.0)

    def test_missing_total_commits_defaults_to_zero(self):
        result = calculate_activity_score({})
        self.assertAlmostEqual(result, 0.0)

    def test_precise_value_no_bonus(self):
        result = calculate_activity_score({"total_commits": 9})
        self.assertEqual(result, 20.0)

    def test_precise_value_with_bonus(self):
        result = calculate_activity_score({
            "total_commits": 9,
            "latest_commit_date": _recent_date(),
        })
        self.assertEqual(result, 30.0)

    def test_stale_commit_gets_no_bonus(self):
        result = calculate_activity_score({
            "total_commits": 9,
            "latest_commit_date": _stale_date(),
        })
        self.assertEqual(result, 20.0)

    def test_unparseable_date_gets_no_bonus(self):
        result = calculate_activity_score({
            "total_commits": 9,
            "latest_commit_date": "not-a-date",
        })
        self.assertEqual(result, 20.0)

    def test_rounds_to_two_decimals(self):
        result = calculate_activity_score({"total_commits": 10})
        self.assertEqual(result, 20.83)

    def test_capped_at_100_without_bonus(self):
        result = calculate_activity_score({"total_commits": 99999})
        self.assertEqual(result, 100.0)

    def test_bonus_beyond_cap_still_100(self):
        result = calculate_activity_score({
            "total_commits": 99999,
            "latest_commit_date": _recent_date(),
        })
        self.assertEqual(result, 100.0)


class TestCalculateCommunityScore(unittest.TestCase):
    def test_zero_contributors_and_issues(self):
        result = calculate_community_score(
            {"total_contributors": 0},
            {"total_issues": 0, "closed_issues": 0},
        )
        self.assertAlmostEqual(result, 0.0)

    def test_with_contributors_and_no_issues(self):
        result = calculate_community_score(
            {"total_contributors": 10},
            {"total_issues": 0, "closed_issues": 0},
        )
        self.assertAlmostEqual(result, 25.0)

    def test_with_contributors_and_issues(self):
        result = calculate_community_score(
            {"total_contributors": 10},
            {"total_issues": 20, "closed_issues": 15},
        )
        self.assertAlmostEqual(result, 62.5)

    def test_score_capped_at_100(self):
        result = calculate_community_score(
            {"total_contributors": 100},
            {"total_issues": 100, "closed_issues": 100},
        )
        self.assertLessEqual(result, 100.0)

    def test_missing_keys_defaults_to_zero(self):
        result = calculate_community_score({}, {})
        self.assertAlmostEqual(result, 0.0)

    def test_issue_score_only(self):
        result = calculate_community_score(
            {"total_contributors": 0},
            {"total_issues": 10, "closed_issues": 5},
        )
        self.assertAlmostEqual(result, 25.0)

    def test_contributor_score_caps_at_50(self):
        result = calculate_community_score(
            {"total_contributors": 100},
            {"total_issues": 0, "closed_issues": 0},
        )
        self.assertEqual(result, 50.0)

    def test_precise_rounding(self):
        result = calculate_community_score(
            {"total_contributors": 3},
            {"total_issues": 3, "closed_issues": 1},
        )
        self.assertEqual(result, 24.17)

    def test_exact_cap_100(self):
        result = calculate_community_score(
            {"total_contributors": 100},
            {"total_issues": 100, "closed_issues": 100},
        )
        self.assertEqual(result, 100.0)

    def test_all_issues_closed_full_issue_score(self):
        result = calculate_community_score(
            {"total_contributors": 0},
            {"total_issues": 5, "closed_issues": 5},
        )
        self.assertEqual(result, 50.0)


class TestCalculateMaintainabilityScore(unittest.TestCase):
    def test_repo_with_stars_and_forks(self):
        result = calculate_maintainability_score({
            "stars": 100,
            "forks": 50,
            "description": "A repo",
            "language": "Python",
        })
        self.assertTrue(result > 0)
        self.assertLessEqual(result, 100.0)

    def test_repo_with_no_stars_or_forks(self):
        result = calculate_maintainability_score({
            "stars": 0,
            "forks": 0,
            "description": None,
            "language": None,
        })
        self.assertAlmostEqual(result, 0.0)

    def test_repo_without_description(self):
        result = calculate_maintainability_score({
            "stars": 0,
            "forks": 0,
            "description": None,
            "language": "Python",
        })
        self.assertAlmostEqual(result, 15.0)

    def test_repo_without_language(self):
        result = calculate_maintainability_score({
            "stars": 0,
            "forks": 0,
            "description": "A repo",
            "language": None,
        })
        self.assertAlmostEqual(result, 15.0)

    def test_repo_with_empty_string_description(self):
        result = calculate_maintainability_score({
            "stars": 0,
            "forks": 0,
            "description": "",
            "language": "Python",
        })
        self.assertAlmostEqual(result, 15.0)

    def test_missing_keys_defaults_to_zero(self):
        result = calculate_maintainability_score({})
        self.assertAlmostEqual(result, 0.0)

    def test_score_capped_at_100(self):
        result = calculate_maintainability_score({
            "stars": 100000,
            "forks": 100000,
            "description": "A repo",
            "language": "Python",
        })
        self.assertLessEqual(result, 100.0)

    def test_both_metadata_no_stars_or_forks(self):
        result = calculate_maintainability_score({
            "stars": 0,
            "forks": 0,
            "description": "A repo",
            "language": "Python",
        })
        self.assertEqual(result, 30.0)

    def test_precise_stars_only(self):
        result = calculate_maintainability_score({
            "stars": 9,
            "forks": 0,
            "description": None,
            "language": None,
        })
        self.assertEqual(result, 10.0)

    def test_whitespace_description_is_truthy(self):
        result = calculate_maintainability_score({
            "stars": 0,
            "forks": 0,
            "description": " ",
            "language": None,
        })
        self.assertEqual(result, 15.0)

    def test_stars_capped_at_40(self):
        result = calculate_maintainability_score({
            "stars": 100000,
            "forks": 0,
            "description": None,
            "language": None,
        })
        self.assertEqual(result, 40.0)

    def test_forks_capped_at_30(self):
        result = calculate_maintainability_score({
            "stars": 0,
            "forks": 100000,
            "description": None,
            "language": None,
        })
        self.assertEqual(result, 30.0)

    def test_full_score_exact_100(self):
        result = calculate_maintainability_score({
            "stars": 100000,
            "forks": 100000,
            "description": "A repo",
            "language": "Python",
        })
        self.assertEqual(result, 100.0)


class TestCalculateHealthScore(unittest.TestCase):
    def test_health_score_averages_subscores(self):
        analysis = {
            "commits": {"total_commits": 10, "latest_commit_date": _recent_date()},
            "contributors": {"total_contributors": 5},
            "issues": {"total_issues": 10, "closed_issues": 5},
            "repo": {"stars": 10, "forks": 5, "description": "A", "language": "Python"},
        }

        result = calculate_health_score(analysis)
        self.assertTrue(0.0 <= result <= 100.0)

    def test_health_score_with_empty_analysis(self):
        result = calculate_health_score({})
        self.assertTrue(0.0 <= result <= 100.0)

    def test_health_score_returns_float(self):
        analysis = {
            "commits": {},
            "contributors": {},
            "issues": {},
            "repo": {},
        }
        result = calculate_health_score(analysis)
        self.assertIsInstance(result, float)

    def test_exact_average_of_subscores(self):
        analysis = {
            "commits": {"total_commits": 99},
            "contributors": {},
            "issues": {},
            "repo": {},
        }

        result = calculate_health_score(analysis)

        self.assertEqual(result, 13.33)


class TestGradeScore(unittest.TestCase):
    def test_grade_a(self):
        self.assertEqual(grade_score(95), "A")
        self.assertEqual(grade_score(100), "A")

    def test_grade_b(self):
        self.assertEqual(grade_score(85), "B")
        self.assertEqual(grade_score(80), "B")

    def test_grade_c(self):
        self.assertEqual(grade_score(75), "C")
        self.assertEqual(grade_score(70), "C")

    def test_grade_d(self):
        self.assertEqual(grade_score(65), "D")
        self.assertEqual(grade_score(60), "D")

    def test_grade_f(self):
        self.assertEqual(grade_score(50), "F")
        self.assertEqual(grade_score(0), "F")
        self.assertEqual(grade_score(59.9), "F")

    def test_boundary_a(self):
        self.assertEqual(grade_score(89.99), "B")
        self.assertEqual(grade_score(90.0), "A")

    def test_boundary_b(self):
        self.assertEqual(grade_score(79.99), "C")
        self.assertEqual(grade_score(80.0), "B")

    def test_boundary_c(self):
        self.assertEqual(grade_score(69.99), "D")
        self.assertEqual(grade_score(70.0), "C")

    def test_boundary_d(self):
        self.assertEqual(grade_score(59.99), "F")
        self.assertEqual(grade_score(60.0), "D")

    def test_negative_score(self):
        self.assertEqual(grade_score(-10), "F")

    def test_above_100(self):
        self.assertEqual(grade_score(150), "A")


if __name__ == "__main__":
    unittest.main()
