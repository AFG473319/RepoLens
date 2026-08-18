import unittest
import json
from unittest.mock import patch, MagicMock
from report import (
    generate_text_report,
    generate_json_report,
    save_report,
    print_summary,
)


class TestGenerateTextReport(unittest.TestCase):
    def test_returns_string(self):
        analysis = {
            "repo": {"name": "test", "description": "desc", "stars": 10, "forks": 2, "language": "Python"},
            "commits": {"total_commits": 50, "unique_contributors": 3, "latest_commit_date": "2024-06-15"},
            "contributors": {"total_contributors": 3, "top_contributor": "Alice", "most_contributions": 20},
            "languages": {"primary_language": "Python", "language_count": 1},
            "issues": {"total_issues": 10, "open_issues": 5, "closed_issues": 5},
        }
        scores = {
            "health_score": 85.5,
            "activity_score": 70.0,
            "community_score": 60.0,
            "maintainability_score": 90.0,
            "grade": "B",
        }

        result = generate_text_report(analysis, scores)

        self.assertIsInstance(result, str)
        self.assertIn("RepoLens Analysis Report", result)
        self.assertIn("test", result)
        self.assertIn("85.5", result)
        self.assertIn("Grade: B", result)

    def test_contains_all_sections(self):
        analysis = {"repo": {}, "commits": {}, "contributors": {}, "languages": {}, "issues": {}}
        scores = {}

        result = generate_text_report(analysis, scores)

        self.assertIn("Repository Info", result)
        self.assertIn("Commits", result)
        self.assertIn("Contributors", result)
        self.assertIn("Languages", result)
        self.assertIn("Issues", result)
        self.assertIn("Scores", result)

    def test_handles_missing_keys(self):
        analysis = {}
        scores = {}

        result = generate_text_report(analysis, scores)

        self.assertIsInstance(result, str)
        self.assertIn("None", result)


class TestGenerateJsonReport(unittest.TestCase):
    def test_returns_valid_json(self):
        analysis = {"repo": {"name": "test"}}
        scores = {"health_score": 90.0}

        result = generate_json_report(analysis, scores)

        parsed = json.loads(result)
        self.assertIn("analysis", parsed)
        self.assertIn("scores", parsed)

    def test_json_contains_correct_data(self):
        analysis = {"repo": {"name": "my-repo"}}
        scores = {"health_score": 95.0}

        result = generate_json_report(analysis, scores)

        parsed = json.loads(result)
        self.assertEqual(parsed["analysis"]["repo"]["name"], "my-repo")
        self.assertEqual(parsed["scores"]["health_score"], 95.0)

    def test_json_is_pretty_printed(self):
        analysis = {}
        scores = {}

        result = generate_json_report(analysis, scores)

        self.assertIn("\n", result)
        self.assertIn("    ", result)


class TestSaveReport(unittest.TestCase):
    @patch("builtins.open", unittest.mock.mock_open())
    def test_save_report_creates_file(self):
        report_content = "Test report content"
        filename = "test_report.txt"

        save_report(report_content, filename)

        open.assert_called_once_with(filename, "w")

    @patch("builtins.open", unittest.mock.mock_open())
    def test_save_report_writes_content(self):
        report_content = "Hello World"
        filename = "output.txt"

        save_report(report_content, filename)

        open().write.assert_called_once_with("Hello World")


class TestPrintSummary(unittest.TestCase):
    @patch("builtins.print")
    def test_print_summary_outputs_scores(self, mock_print):
        scores = {
            "health_score": 85.5,
            "grade": "B",
        }

        print_summary(scores)

        self.assertTrue(mock_print.called)
        calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any("85.5" in call for call in calls))
        self.assertTrue(any("B" in call for call in calls))

    @patch("builtins.print")
    def test_print_summary_with_empty_scores(self, mock_print):
        scores = {}

        print_summary(scores)

        self.assertTrue(mock_print.called)


if __name__ == "__main__":
    unittest.main()
