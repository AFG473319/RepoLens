import unittest
from analyzer import (
    analyze_repo,
    analyze_commits,
    analyze_contributors,
    analyze_languages,
    analyze_issues,
)


class TestAnalyzeRepo(unittest.TestCase):
    def test_analyze_repo_with_full_data(self):
        repo_data = {
            "name": "my-repo",
            "description": "A test repo",
            "stargazers_count": 42,
            "forks_count": 7,
            "language": "Python",
        }

        result = analyze_repo(repo_data)

        self.assertEqual(result["name"], "my-repo")
        self.assertEqual(result["description"], "A test repo")
        self.assertEqual(result["stars"], 42)
        self.assertEqual(result["forks"], 7)
        self.assertEqual(result["language"], "Python")

    def test_analyze_repo_with_missing_keys(self):
        repo_data = {}

        result = analyze_repo(repo_data)

        self.assertIsNone(result["name"])
        self.assertIsNone(result["description"])
        self.assertIsNone(result["stars"])
        self.assertIsNone(result["forks"])
        self.assertIsNone(result["language"])

    def test_analyze_repo_returns_dict(self):
        repo_data = {"name": "test"}
        result = analyze_repo(repo_data)
        self.assertIsInstance(result, dict)
        self.assertIn("name", result)


class TestAnalyzeCommits(unittest.TestCase):
    def test_analyze_commits_with_multiple_authors(self):
        commits = [
            {"commit": {"author": {"name": "Alice", "date": "2024-01-01"}}},
            {"commit": {"author": {"name": "Bob", "date": "2024-01-02"}}},
            {"commit": {"author": {"name": "Alice", "date": "2024-01-03"}}},
        ]

        result = analyze_commits(commits)

        self.assertEqual(result["total_commits"], 3)
        self.assertEqual(result["unique_contributors"], 2)
        self.assertEqual(result["latest_commit_date"], "2024-01-03")

    def test_analyze_commits_with_empty_list(self):
        result = analyze_commits([])

        self.assertEqual(result["total_commits"], 0)
        self.assertEqual(result["unique_contributors"], 0)
        self.assertIsNone(result["latest_commit_date"])

    def test_analyze_commits_with_single_commit(self):
        commits = [
            {"commit": {"author": {"name": "Alice", "date": "2024-06-15"}}}
        ]

        result = analyze_commits(commits)

        self.assertEqual(result["total_commits"], 1)
        self.assertEqual(result["unique_contributors"], 1)
        self.assertEqual(result["latest_commit_date"], "2024-06-15")


class TestAnalyzeContributors(unittest.TestCase):
    def test_analyze_contributors_finds_top(self):
        contributors = [
            {"login": "Bob", "contributions": 25},
            {"login": "Alice", "contributions": 10},
            {"login": "Charlie", "contributions": 5},
        ]

        result = analyze_contributors(contributors)

        self.assertEqual(result["total_contributors"], 3)
        self.assertEqual(result["top_contributor"], "Bob")
        self.assertEqual(result["most_contributions"], 25)

    def test_analyze_contributors_empty_list(self):
        result = analyze_contributors([])

        self.assertEqual(result["total_contributors"], 0)
        self.assertIsNone(result["top_contributor"])
        self.assertEqual(result["most_contributions"], 0)

    def test_analyze_contributors_single_contributor(self):
        contributors = [
            {"login": "Alice", "contributions": 100},
        ]

        result = analyze_contributors(contributors)

        self.assertEqual(result["total_contributors"], 1)
        self.assertEqual(result["top_contributor"], "Alice")
        self.assertEqual(result["most_contributions"], 100)


class TestAnalyzeLanguages(unittest.TestCase):
    def test_analyze_languages_finds_primary(self):
        languages = {"Python": 1000, "JavaScript": 500, "HTML": 200}

        result = analyze_languages(languages)

        self.assertEqual(result["primary_language"], "Python")
        self.assertEqual(result["language_count"], 3)

    def test_analyze_languages_empty_dict(self):
        result = analyze_languages({})

        self.assertIsNone(result["primary_language"])
        self.assertEqual(result["language_count"], 0)

    def test_analyze_languages_single_language(self):
        languages = {"Rust": 800}

        result = analyze_languages(languages)

        self.assertEqual(result["primary_language"], "Rust")
        self.assertEqual(result["language_count"], 1)

    def test_analyze_languages_multiple_languages(self):
        languages = {"Python": 300, "JavaScript": 500}

        result = analyze_languages(languages)

        self.assertEqual(result["primary_language"], "JavaScript")
        self.assertEqual(result["language_count"], 2)


class TestAnalyzeIssues(unittest.TestCase):
    def test_analyze_issues_mixed_states(self):
        issues = [
            {"number": 1, "state": "open"},
            {"number": 2, "state": "closed"},
            {"number": 3, "state": "open"},
            {"number": 4, "state": "closed"},
            {"number": 5, "state": "open"},
        ]

        result = analyze_issues(issues)

        self.assertEqual(result["total_issues"], 5)
        self.assertEqual(result["open_issues"], 3)
        self.assertEqual(result["closed_issues"], 2)

    def test_analyze_issues_empty_list(self):
        result = analyze_issues([])

        self.assertEqual(result["total_issues"], 0)
        self.assertEqual(result["open_issues"], 0)
        self.assertEqual(result["closed_issues"], 0)

    def test_analyze_issues_all_open(self):
        issues = [
            {"number": 1, "state": "open"},
            {"number": 2, "state": "open"},
        ]

        result = analyze_issues(issues)

        self.assertEqual(result["total_issues"], 2)
        self.assertEqual(result["open_issues"], 2)
        self.assertEqual(result["closed_issues"], 0)

    def test_analyze_issues_missing_state_key(self):
        issues = [
            {"number": 1},
            {"number": 2, "state": "closed"},
        ]

        result = analyze_issues(issues)

        self.assertEqual(result["total_issues"], 2)
        self.assertEqual(result["open_issues"], 0)
        self.assertEqual(result["closed_issues"], 1)

    def test_analyze_issues_filters_pull_requests(self):
        issues = [
            {"number": 1, "state": "open"},
            {"number": 2, "state": "closed"},
            {"number": 3, "state": "open", "pull_request": {"url": "..."}},
            {"number": 4, "state": "closed", "pull_request": {"url": "..."}},
        ]

        result = analyze_issues(issues)

        self.assertEqual(result["total_issues"], 2)
        self.assertEqual(result["open_issues"], 1)
        self.assertEqual(result["closed_issues"], 1)


if __name__ == "__main__":
    unittest.main()
