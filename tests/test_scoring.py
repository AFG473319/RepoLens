import unittest
from scoring import (
    calculate_activity_score,
    calculate_community_score,
    calculate_maintainability_score,
    calculate_health_score,
    grade_score,
)


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
            "latest_commit_date": "2024-06-15",
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
            "latest_commit_date": "2024-06-15",
        })
        self.assertLessEqual(result, 100.0)

    def test_missing_total_commits_defaults_to_zero(self):
        result = calculate_activity_score({})
        self.assertAlmostEqual(result, 0.0)


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


class TestCalculateHealthScore(unittest.TestCase):
    def test_health_score_averages_subscores(self):
        analysis = {
            "commits": {"total_commits": 10, "latest_commit_date": "2024-06-15"},
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


if __name__ == "__main__":
    unittest.main()
