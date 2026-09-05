import unittest
import json
import os
import tempfile
from unittest.mock import patch, call, MagicMock

import provider
from report import (
    generate_text_report,
    generate_json_report,
    generate_html_report,
    save_report,
    print_summary,
    REPORT_FORMAT_GENERATORS,
    SUPPORTED_REPORT_FORMATS,
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
            f"more than {provider.MAX_PAGES * provider.PER_PAGE} results", result
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


class TestGenerateHtmlReport(unittest.TestCase):
    def _analysis(self):
        return {
            "repo": {"name": "flask", "description": "A micro framework", "stars": 69500, "forks": 13200, "language": "Python"},
            "commits": {"total_commits": 8500, "unique_contributors": 412, "latest_commit_date": "2026-08-27"},
            "contributors": {"total_contributors": 843, "top_contributor": "mitsuhiko", "most_contributions": 1204},
            "languages": {"primary_language": "Python", "language_count": 7},
            "issues": {"total_issues": 1000, "open_issues": 213, "closed_issues": 787},
        }

    def _scores(self):
        return {
            "health_score": 92.5,
            "activity_score": 95.0,
            "community_score": 96.7,
            "maintainability_score": 85.9,
            "grade": "A",
        }

    def _assert_no_none(self, result):
        # None must never leak into the rendered page (not even inside
        # escaped text, which would show as the literal string "None")
        self.assertNotIn("None", result.replace("<!-- None", ""))

    def test_registry_covers_every_supported_format(self):
        for fmt in SUPPORTED_REPORT_FORMATS:
            self.assertIn(fmt, REPORT_FORMAT_GENERATORS)

    def test_registry_generators_return_strings(self):
        analysis = self._analysis()
        scores = self._scores()
        for fmt, (generator, extension) in REPORT_FORMAT_GENERATORS.items():
            result = generator("pallets", "flask", analysis, scores)
            self.assertIsInstance(result, str)
            self.assertTrue(extension.startswith("."))

    def test_returns_complete_html_document(self):
        result = generate_html_report("pallets", "flask", self._analysis(), self._scores())

        self.assertIsInstance(result, str)
        self.assertIn("<!DOCTYPE html>", result)
        self.assertIn("<html", result)
        self.assertIn("</html>", result)
        self.assertIn("<title>", result)

    def test_contains_hero_and_all_data(self):
        result = generate_html_report("pallets", "flask", self._analysis(), self._scores())

        self.assertIn("flask", result)
        self.assertIn("A micro framework", result)
        self.assertIn("69,500", result)
        self.assertIn("13,200", result)
        self.assertIn("843", result)
        self.assertIn("mitsuhiko", result)
        self.assertIn("1,204", result)
        self.assertIn("2026-08-27", result)
        self.assertIn("92.5", result)
        self.assertIn("95.0", result)
        self.assertIn("96.7", result)
        self.assertIn("85.9", result)
        self.assertIn(">A</span>", result)

    def test_hero_renders_owner_and_repo_distinctly(self):
        # The hero must show {owner} > {repo}; this regressed when the repo
        # name (stored in analysis["repo"]["name"]) was reused for both.
        result = generate_html_report("pallets", "flask", self._analysis(), self._scores())

        self.assertIn('<span class="owner">pallets</span>', result)
        self.assertIn('<span class="sep">&gt;</span>', result)
        self.assertIn('<span class="repo-name">flask</span>', result)
        self.assertIn('<title>RepoLens Report — pallets/flask</title>', result)

    def test_hero_falls_back_to_unknown(self):
        result = generate_html_report("", "", {}, {})

        self.assertIn('<span class="owner">Unknown</span>', result)
        self.assertIn('<span class="repo-name">Unknown</span>', result)

    def test_section_headings_present(self):
        result = generate_html_report("pallets", "flask", self._analysis(), self._scores())

        self.assertIn("scores", result)
        self.assertIn("metrics", result)
        self.assertIn("data &amp; limitations", result)

    def test_approximate_note_when_truncated(self):
        analysis = self._analysis()
        analysis["approximate"] = True
        analysis["truncated_endpoints"] = ["commits", "issues"]

        result = generate_html_report("pallets", "flask", analysis, self._scores())

        self.assertIn("approximate", result)
        self.assertIn(f"more than {provider.MAX_PAGES * provider.PER_PAGE:,} results", result)
        self.assertIn("commits, issues", result)

    def test_no_limitations_when_not_truncated(self):
        analysis = self._analysis()
        analysis["approximate"] = False
        analysis["truncated_endpoints"] = []

        result = generate_html_report("pallets", "flask", analysis, self._scores())

        self.assertIn("No pagination truncation", result)

    def test_escapes_repo_sourced_strings(self):
        analysis = self._analysis()
        analysis["repo"]["description"] = "desc & <b>bold</b> \"quoted\""
        # The owner/repo parameters are external strings rendered into the
        # hero and title; they must be HTML-escaped before interpolation.
        result = generate_html_report(
            'pallets"><script>alert(1)</script>',
            'flask"><script>alert(2)</script>',
            analysis,
            self._scores(),
        )

        self.assertNotIn('<script>alert(1)</script>', result)
        self.assertNotIn('<script>alert(2)</script>', result)
        self.assertIn('&lt;script&gt;alert(1)&lt;/script&gt;', result)
        self.assertIn('&lt;script&gt;alert(2)&lt;/script&gt;', result)
        self.assertIn("desc &amp; &lt;b&gt;bold&lt;/b&gt; &quot;quoted&quot;", result)
        self._assert_no_none(result)

    def test_escapes_truncated_endpoint_names(self):
        analysis = self._analysis()
        analysis["approximate"] = True
        analysis["truncated_endpoints"] = ['<script>x</script>']

        result = generate_html_report("pallets", "flask", analysis, self._scores())

        self.assertNotIn("<script>x</script>", result)

    def test_handles_empty_analysis_and_scores(self):
        result = generate_html_report("pallets", "flask", {}, {})

        self.assertIn("<!DOCTYPE html>", result)
        self._assert_no_none(result)
        self.assertIn("0", result)

    def test_handles_missing_sub_dicts(self):
        analysis = {"approximate": False}
        result = generate_html_report("pallets", "flask", analysis, {})

        self.assertIn("<!DOCTYPE html>", result)
        self._assert_no_none(result)

    def test_none_values_render_placeholders(self):
        # analyzer emits explicit None for null GitHub fields
        analysis = {
            "repo": {"name": None, "description": None, "stars": None, "forks": None, "language": None},
            "commits": {"total_commits": 0, "unique_contributors": 0, "latest_commit_date": None},
            "contributors": {"total_contributors": 0, "top_contributor": None, "most_contributions": 0},
            "languages": {"primary_language": None, "language_count": 0},
            "issues": {"total_issues": 0, "open_issues": 0, "closed_issues": 0},
        }
        result = generate_html_report("pallets", "flask", analysis, {})

        self.assertIn("No description", result)
        self.assertIn("N/A", result)
        self.assertIn("Unknown", result)
        self._assert_no_none(result)

    def test_scores_clamped_to_zero_hundred(self):
        analysis = self._analysis()
        scores = {"health_score": 142.0, "activity_score": -7.0, "community_score": 50.0, "maintainability_score": 100.0, "grade": "A"}
        result = generate_html_report("pallets", "flask", analysis, scores)

        # bars carry width via the --w custom property; clamped to 0-100
        self.assertNotIn("--w: 142%", result)
        self.assertNotIn("--w: -7%", result)
        self.assertIn("--w: 100%", result)
        self.assertIn("--w: 0%", result)

    def test_non_numeric_scores_render_zero_width(self):
        analysis = self._analysis()
        scores = {"health_score": None, "activity_score": "high", "community_score": 50.0, "maintainability_score": 80.0, "grade": "B"}
        result = generate_html_report("pallets", "flask", analysis, scores)

        self.assertNotIn("--w: None%", result)
        self.assertNotIn("--w: high%", result)
        self.assertIn("--w: 0%", result)

    def test_unknown_grade_gets_neutral_style(self):
        analysis = self._analysis()
        scores = self._scores()
        scores["grade"] = "X"
        result = generate_html_report("pallets", "flask", analysis, scores)

        self.assertIn("g-Neutral", result)

    def test_missing_grade_gets_neutral_style(self):
        result = generate_html_report("pallets", "flask", self._analysis(), {"health_score": 50.0})
        self.assertIn("g-Neutral", result)

    def test_unicode_survives(self):
        analysis = self._analysis()
        analysis["repo"]["description"] = "Résumé — 中文说明 🎉"
        result = generate_html_report(
            "pallets", "プロジェクト-ünïcodé", analysis, self._scores()
        )

        self.assertIn("プロジェクト-ünïcodé", result)
        self.assertIn("Résumé — 中文说明", result)

    def test_thousands_separators_on_counts(self):
        result = generate_html_report("pallets", "flask", self._analysis(), self._scores())
        self.assertIn("69,500", result)
        self.assertIn("8,500", result)


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

    def test_json_includes_truncation_flags(self):
        analysis = {
            "repo": {"name": "test"},
            "approximate": True,
            "truncated_endpoints": ["commits", "issues"],
        }
        scores = {"health_score": 85.5}

        parsed = json.loads(generate_json_report(analysis, scores))

        self.assertTrue(parsed["approximate"])
        self.assertEqual(parsed["truncated_endpoints"], ["commits", "issues"])
        self.assertTrue(parsed["analysis"]["approximate"])

    def test_json_defaults_truncation_flags_when_missing(self):
        analysis = {"repo": {"name": "test"}}
        scores = {}

        result = generate_json_report(analysis, scores)

        self.assertEqual(
            json.loads(result)["approximate"], False,
        )
        self.assertEqual(
            json.loads(result)["truncated_endpoints"], [],
        )

    def test_round_trip_equality(self):
        analysis = {
            "repo": {"name": "test"},
            "issues": {"total_issues": 5},
            "approximate": False,
            "truncated_endpoints": [],
        }
        scores = {"health_score": 85.5, "grade": "B"}

        parsed = json.loads(generate_json_report(analysis, scores))

        self.assertEqual(
            parsed,
            {
                "analysis": analysis,
                "scores": scores,
                "platform": "GitHub",
                "approximate": False,
                "truncated_endpoints": [],
                "language_error": False,
            },
        )

    def test_empty_inputs_still_valid(self):
        result = generate_json_report({}, {})

        self.assertEqual(
            json.loads(result),
            {
                "analysis": {},
                "scores": {},
                "platform": "GitHub",
                "approximate": False,
                "truncated_endpoints": [],
                "language_error": False,
            },
        )


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

    @patch("builtins.print")
    def test_print_summary_warns_when_approximate(self, mock_print):
        scores = {"health_score": 85.5, "grade": "B"}
        analysis = {
            "approximate": True,
            "truncated_endpoints": ["commits", "issues"],
        }

        print_summary(scores, analysis)

        calls = [str(call) for call in mock_print.call_args_list]
        self.assertTrue(any("approximate" in call.lower() for call in calls))
        self.assertTrue(
            any(f"{provider.MAX_PAGES * provider.PER_PAGE} results" in call
                for call in calls)
        )
        self.assertTrue(any("Truncated endpoints: commits, issues" in call
                            for call in calls))

    @patch("builtins.print")
    def test_print_summary_no_warning_without_analysis(self, mock_print):
        scores = {"health_score": 85.5, "grade": "B"}

        print_summary(scores)

        calls = [str(call) for call in mock_print.call_args_list]
        self.assertFalse(any("Warning" in call for call in calls))

    @patch("builtins.print")
    def test_print_summary_no_warning_when_not_approximate(self, mock_print):
        scores = {"health_score": 85.5, "grade": "B"}
        analysis = {"approximate": False, "truncated_endpoints": []}

        print_summary(scores, analysis)

        calls = [str(call) for call in mock_print.call_args_list]
        self.assertFalse(any("Warning" in call for call in calls))



class TestPlatformAwareWording(unittest.TestCase):
    """F4/F2: reports must name the right platform and flag missing languages."""

    def _analysis(self, **extra):
        analysis = {
            "repo": {"name": "test", "stars": 1, "forks": 1, "language": "Python"},
            "commits": {"total_commits": 1},
            "contributors": {"total_contributors": 1},
            "languages": {"primary_language": "Python", "language_count": 1},
            "issues": {"total_issues": 0},
            "approximate": True,
            "truncated_endpoints": ["commits"],
        }
        analysis.update(extra)
        return analysis

    def _scores(self):
        return {"health_score": 80.0, "grade": "B"}

    def test_text_report_names_gitlab_endpoints(self):
        result = generate_text_report(self._analysis(), self._scores(), platform="gitlab")
        self.assertIn("one or more GitLab endpoints", result)

    def test_text_report_defaults_to_github(self):
        result = generate_text_report(self._analysis(), self._scores())
        self.assertIn("one or more GitHub endpoints", result)

    def test_text_report_notes_language_error(self):
        result = generate_text_report(self._analysis(language_error=True), self._scores())
        self.assertIn("Language data could not be fetched", result)

    def test_summary_names_gitlab_endpoints(self):
        with patch("builtins.print") as mock_print:
            print_summary(self._scores(), self._analysis(), platform="gitlab")
        outputs = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("GitLab endpoints", outputs)

    def test_summary_warns_about_language_error(self):
        with patch("builtins.print") as mock_print:
            print_summary(self._scores(), self._analysis(language_error=True))
        outputs = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("language data could not be fetched", outputs)

    def test_html_report_names_gitlab_endpoints(self):
        result = generate_html_report("g", "p", self._analysis(), self._scores(), platform="gitlab")
        self.assertIn("GitLab endpoints", result)

    def test_html_report_notes_language_error(self):
        result = generate_html_report("g", "p", self._analysis(language_error=True), self._scores())
        self.assertIn("Language data unavailable", result)


if __name__ == "__main__":
    unittest.main()
