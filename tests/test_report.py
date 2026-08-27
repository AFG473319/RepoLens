import unittest
import json
import os
import tempfile
from unittest.mock import patch, call, MagicMock

import github
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
        self.assertIn("Unknown", result)
        self.assertIn("No description", result)
        self.assertNotIn("None", result)

    def test_approximate_note_when_truncated(self):
        analysis = {
            "approximate": True,
            "truncated_endpoints": ["commits", "issues"],
        }
        scores = {}

        result = generate_text_report(analysis, scores)

        self.assertIn("approximated", result)
        self.assertIn(
            f"more than {github.MAX_PAGES * github.PER_PAGE} results", result
        )
        self.assertIn("Truncated endpoints: commits, issues", result)

    def test_no_approximate_note_when_not_truncated(self):
        analysis = {"repo": {}}
        scores = {}

        result = generate_text_report(analysis, scores)

        self.assertNotIn("approximated", result)

    def test_complete_report_specific_lines(self):
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

        for line in (
            "  Name: test",
            "  Description: desc",
            "  Stars: 10",
            "  Forks: 2",
            "  Language: Python",
            "  Total commits: 50",
            "  Unique contributors: 3",
            "  Latest commit date: 2024-06-15",
            "  Total contributors: 3",
            "  Top contributor: Alice",
            "  Most contributions: 20",
            "  Primary language: Python",
            "  Language count: 1",
            "  Total issues: 10",
            "  Open issues: 5",
            "  Closed issues: 5",
            "  Health score: 85.5",
            "  Activity score: 70.0",
            "  Community score: 60.0",
            "  Maintainability score: 90.0",
            "  Grade: B",
        ):
            self.assertIn(line, result)

    def test_defaults_for_missing_optional_fields(self):
        analysis = {"repo": {}, "commits": {}, "contributors": {}, "languages": {}, "issues": {}}
        scores = {}

        result = generate_text_report(analysis, scores)

        self.assertIn("  Latest commit date: N/A", result)
        self.assertIn("  Top contributor: N/A", result)
        self.assertIn("  Primary language: Unknown", result)
        self.assertIn("  Grade: N/A", result)


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

    def test_round_trip_equality(self):
        analysis = {"repo": {"name": "test"}, "issues": {"total_issues": 5}}
        scores = {"health_score": 85.5, "grade": "B"}

        parsed = json.loads(generate_json_report(analysis, scores))

        self.assertEqual(parsed, {"analysis": analysis, "scores": scores})

    def test_empty_inputs_still_valid(self):
        result = generate_json_report({}, {})

        self.assertEqual(json.loads(result), {"analysis": {}, "scores": {}})


class TestSaveReport(unittest.TestCase):
    @patch("builtins.open", unittest.mock.mock_open())
    def test_save_report_creates_file(self):
        report_content = "Test report content"
        filename = "test_report.txt"

        save_report(report_content, filename)

        open.assert_called_once_with(filename, "w", encoding="utf-8")

    @patch("builtins.open", unittest.mock.mock_open())
    def test_save_report_writes_content(self):
        report_content = "Hello World"
        filename = "output.txt"

        save_report(report_content, filename)

        open().write.assert_called_once_with("Hello World")

    def test_save_report_writes_actual_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            filename = os.path.join(tmpdir, "report.txt")

            save_report("content here", filename)

            with open(filename, "r", encoding="utf-8") as file_handle:
                self.assertEqual(file_handle.read(), "content here")


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

    @patch("builtins.print")
    def test_print_summary_exact_output(self, mock_print):
        scores = {"health_score": 85.5, "grade": "B"}

        print_summary(scores)

        self.assertEqual(
            mock_print.call_args_list,
            [call("Summary"), call("  Health score: 85.5"), call("  Grade: B")],
        )


if __name__ == "__main__":
    unittest.main()
