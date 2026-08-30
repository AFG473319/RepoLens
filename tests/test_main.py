import unittest
from unittest.mock import MagicMock, patch

import requests

import main


ANALYSIS_DICT = {
    "repo": {},
    "commits": {},
    "contributors": {},
    "languages": {},
    "issues": {},
}

SCORES_DICT = {
    "health_score": 85.0,
    "activity_score": 70.0,
    "community_score": 60.0,
    "maintainability_score": 90.0,
    "grade": "B",
}


class TestAnalyzeRepository(unittest.TestCase):
    @patch("main.github")
    @patch("main.analyzer")
    @patch("main.scoring")
    def test_analyze_repository_pipeline(self, mock_scoring, mock_analyzer, mock_github):
        mock_github.get_repo.return_value = {"name": "test-repo"}
        mock_github.get_commits.return_value = (
            [{"commit": {"author": {"name": "Alice", "date": "2024-06-15"}}}], False,
        )
        mock_github.get_contributors.return_value = (
            [{"login": "Alice", "contributions": 10}], False,
        )
        mock_github.get_languages.return_value = {"Python": 1000}
        mock_github.get_issues.return_value = (
            [{"state": "open"}, {"state": "closed"}], False,
        )

        mock_analyzer.analyze_repo.return_value = {"name": "test-repo", "stars": 10}
        mock_analyzer.analyze_commits.return_value = {"total_commits": 1, "unique_contributors": 1, "latest_commit_date": "2024-06-15"}
        mock_analyzer.analyze_contributors.return_value = {"total_contributors": 1, "top_contributor": "Alice", "most_contributions": 10}
        mock_analyzer.analyze_languages.return_value = {"primary_language": "Python", "language_count": 1}
        mock_analyzer.analyze_issues.return_value = {"total_issues": 2, "open_issues": 1, "closed_issues": 1}

        mock_scoring.calculate_health_score.return_value = 85.0
        mock_scoring.calculate_activity_score.return_value = 70.0
        mock_scoring.calculate_community_score.return_value = 60.0
        mock_scoring.calculate_maintainability_score.return_value = 90.0
        mock_scoring.grade_score.return_value = "B"

        analysis, scores = main.analyze_repository("owner", "repo")

        self.assertIn("repo", analysis)
        self.assertIn("commits", analysis)
        self.assertIn("contributors", analysis)
        self.assertIn("languages", analysis)
        self.assertIn("issues", analysis)

        self.assertEqual(scores["health_score"], 85.0)
        self.assertEqual(scores["activity_score"], 70.0)
        self.assertEqual(scores["community_score"], 60.0)
        self.assertEqual(scores["maintainability_score"], 90.0)
        self.assertEqual(scores["grade"], "B")

    @patch("main.github")
    @patch("main.analyzer")
    @patch("main.scoring")
    def test_approximate_flag_set_when_endpoint_truncated(
        self, mock_scoring, mock_analyzer, mock_github
    ):
        mock_github.get_repo.return_value = {}
        mock_github.get_commits.return_value = ([{"n": 1}], True)
        mock_github.get_contributors.return_value = ([], False)
        mock_github.get_languages.return_value = {}
        mock_github.get_issues.return_value = ([], False)

        for name in (
            "analyze_repo",
            "analyze_commits",
            "analyze_contributors",
            "analyze_languages",
            "analyze_issues",
        ):
            getattr(mock_analyzer, name).return_value = {}
        mock_scoring.calculate_health_score.return_value = 0.0

        analysis, _scores = main.analyze_repository("owner", "repo")

        self.assertTrue(analysis["approximate"])
        self.assertEqual(analysis["truncated_endpoints"], ["commits"])

    @patch("main.github")
    @patch("main.analyzer")
    @patch("main.scoring")
    def test_approximate_flag_unset_when_nothing_truncated(
        self, mock_scoring, mock_analyzer, mock_github
    ):
        mock_github.get_repo.return_value = {}
        mock_github.get_commits.return_value = ([], False)
        mock_github.get_contributors.return_value = ([], False)
        mock_github.get_languages.return_value = {}
        mock_github.get_issues.return_value = ([], False)

        for name in (
            "analyze_repo",
            "analyze_commits",
            "analyze_contributors",
            "analyze_languages",
            "analyze_issues",
        ):
            getattr(mock_analyzer, name).return_value = {}
        mock_scoring.calculate_health_score.return_value = 0.0

        analysis, _scores = main.analyze_repository("owner", "repo")

        self.assertFalse(analysis["approximate"])
        self.assertEqual(analysis["truncated_endpoints"], [])

    @patch("main.dotenv.load_dotenv")
    @patch("main.os.getenv")
    @patch("main.github")
    @patch("main.analyzer")
    @patch("main.scoring")
    def test_api_key_from_env_is_passed(
        self, mock_scoring, mock_analyzer, mock_github, mock_getenv, mock_load_dotenv
    ):
        mock_getenv.return_value = "secret"
        mock_github.get_repo.return_value = {}
        mock_github.get_commits.return_value = ([], False)
        mock_github.get_contributors.return_value = ([], False)
        mock_github.get_languages.return_value = {}
        mock_github.get_issues.return_value = ([], False)

        mock_analyzer.analyze_repo.return_value = {}
        mock_analyzer.analyze_commits.return_value = {}
        mock_analyzer.analyze_contributors.return_value = {}
        mock_analyzer.analyze_languages.return_value = {}
        mock_analyzer.analyze_issues.return_value = {}

        mock_scoring.calculate_health_score.return_value = 0.0
        mock_scoring.calculate_activity_score.return_value = 0.0
        mock_scoring.calculate_community_score.return_value = 0.0
        mock_scoring.calculate_maintainability_score.return_value = 0.0
        mock_scoring.grade_score.return_value = "F"

        main.analyze_repository("owner", "repo")

        mock_github.get_repo.assert_called_once_with("owner", "repo", api_key="secret")
        mock_github.get_commits.assert_called_once_with("owner", "repo", "secret")
        mock_github.get_contributors.assert_called_once_with("owner", "repo", "secret")
        mock_github.get_languages.assert_called_once_with("owner", "repo", "secret")
        mock_github.get_issues.assert_called_once_with("owner", "repo", "secret")

    @patch("main.github")
    @patch("main.analyzer")
    @patch("main.scoring")
    def test_analyzer_receives_raw_data(self, mock_scoring, mock_analyzer, mock_github):
        repo_data = {"name": "test-repo"}
        commits_data = [{"sha": "abc"}]
        contributors_data = [{"login": "Alice"}]
        languages_data = {"Python": 10}
        issues_data = [{"state": "open"}]

        mock_github.get_repo.return_value = repo_data
        mock_github.get_commits.return_value = (commits_data, False)
        mock_github.get_contributors.return_value = (contributors_data, False)
        mock_github.get_languages.return_value = languages_data
        mock_github.get_issues.return_value = (issues_data, False)

        mock_analyzer.analyze_repo.return_value = {}
        mock_analyzer.analyze_commits.return_value = {}
        mock_analyzer.analyze_contributors.return_value = {}
        mock_analyzer.analyze_languages.return_value = {}
        mock_analyzer.analyze_issues.return_value = {}

        mock_scoring.calculate_health_score.return_value = 0.0
        mock_scoring.calculate_activity_score.return_value = 0.0
        mock_scoring.calculate_community_score.return_value = 0.0
        mock_scoring.calculate_maintainability_score.return_value = 0.0
        mock_scoring.grade_score.return_value = "F"

        main.analyze_repository("owner", "repo")

        mock_analyzer.analyze_repo.assert_called_once_with(repo_data)
        mock_analyzer.analyze_commits.assert_called_once_with(commits_data)
        mock_analyzer.analyze_contributors.assert_called_once_with(contributors_data)
        mock_analyzer.analyze_languages.assert_called_once_with(languages_data)
        mock_analyzer.analyze_issues.assert_called_once_with(issues_data)

    @patch("main.github")
    @patch("main.analyzer")
    @patch("main.scoring")
    def test_scoring_receives_analysis_subdicts(self, mock_scoring, mock_analyzer, mock_github):
        mock_github.get_repo.return_value = {}
        mock_github.get_commits.return_value = ([], False)
        mock_github.get_contributors.return_value = ([], False)
        mock_github.get_languages.return_value = {}
        mock_github.get_issues.return_value = ([], False)

        mock_analyzer.analyze_repo.return_value = {"stars": 1}
        mock_analyzer.analyze_commits.return_value = {"total_commits": 1}
        mock_analyzer.analyze_contributors.return_value = {"total_contributors": 1}
        mock_analyzer.analyze_languages.return_value = {"language_count": 1}
        mock_analyzer.analyze_issues.return_value = {"total_issues": 1}

        mock_scoring.calculate_health_score.return_value = 0.0
        mock_scoring.calculate_activity_score.return_value = 0.0
        mock_scoring.calculate_community_score.return_value = 0.0
        mock_scoring.calculate_maintainability_score.return_value = 0.0
        mock_scoring.grade_score.return_value = "F"

        main.analyze_repository("owner", "repo")

        mock_scoring.calculate_activity_score.assert_called_once_with({"total_commits": 1})
        mock_scoring.calculate_community_score.assert_called_once_with(
            {"total_contributors": 1}, {"total_issues": 1}
        )
        mock_scoring.calculate_maintainability_score.assert_called_once_with({"stars": 1})

        health_arg = mock_scoring.calculate_health_score.call_args[0][0]
        self.assertEqual(
            set(health_arg.keys()),
            {
                "repo",
                "commits",
                "contributors",
                "languages",
                "issues",
                "approximate",
                "truncated_endpoints",
            },
        )


class TestMain(unittest.TestCase):
    @patch("main.menu")
    @patch("main.analyze_repository")
    @patch("main.report")
    def test_main_analyze_flow(self, mock_report, mock_analyze, mock_menu):
        mock_menu.print_banner.return_value = None
        mock_menu.show_menu.return_value = None
        mock_menu.get_user_choice.side_effect = ["Analyze a repository", "Exit"]
        mock_menu.prompt_repo_input.return_value = ("owner", "repo")
        mock_menu.prompt_report_format.return_value = "text"
        mock_menu.confirm_exit.return_value = True

        mock_analyze.return_value = (ANALYSIS_DICT, SCORES_DICT)

        mock_report.print_summary.return_value = None
        mock_report.generate_text_report.return_value = "report text"
        mock_report.save_report.return_value = None

        with patch("builtins.print"):
            with patch("builtins.input", return_value=""):
                main.main()

        mock_menu.print_banner.assert_called()
        mock_analyze.assert_called_once_with("owner", "repo")
        mock_report.print_summary.assert_called_once()
        mock_report.save_report.assert_called_once()

    @patch("main.menu")
    def test_main_exit_immediately(self, mock_menu):
        mock_menu.print_banner.return_value = None
        mock_menu.show_menu.return_value = None
        mock_menu.get_user_choice.return_value = "Exit"
        mock_menu.confirm_exit.return_value = True

        with patch("builtins.print"):
            main.main()

        mock_menu.confirm_exit.assert_called_once()

    @patch("main.menu")
    def test_main_exit_cancelled(self, mock_menu):
        mock_menu.print_banner.return_value = None
        mock_menu.show_menu.return_value = None
        mock_menu.get_user_choice.side_effect = ["Exit", "Exit"]
        mock_menu.confirm_exit.side_effect = [False, True]

        with patch("builtins.print"):
            main.main()

        self.assertEqual(mock_menu.confirm_exit.call_count, 2)

    @patch("main.menu")
    @patch("main.analyze_repository")
    def test_main_handles_exception(self, mock_analyze, mock_menu):
        mock_menu.print_banner.return_value = None
        mock_menu.show_menu.return_value = None
        mock_menu.get_user_choice.side_effect = ["Analyze a repository", "Exit"]
        mock_menu.prompt_repo_input.return_value = ("owner", "repo")
        mock_menu.prompt_report_format.return_value = "text"
        mock_menu.confirm_exit.return_value = True
        mock_analyze.side_effect = requests.RequestException("API Error")

        with patch("builtins.print"):
            with patch("builtins.input", return_value=""):
                main.main()

        mock_analyze.assert_called_once_with("owner", "repo")

    @patch("main.menu")
    @patch("main.analyze_repository")
    @patch("main.report")
    def test_main_json_report_flow(self, mock_report, mock_analyze, mock_menu):
        mock_menu.get_user_choice.side_effect = ["Analyze a repository", "Exit"]
        mock_menu.prompt_repo_input.return_value = ("owner", "repo")
        mock_menu.prompt_report_format.return_value = "json"
        mock_menu.confirm_exit.return_value = True
        mock_analyze.return_value = (ANALYSIS_DICT, SCORES_DICT)
        mock_report.generate_json_report.return_value = '{"analysis": {}, "scores": {}}'

        with patch("builtins.print"):
            with patch("builtins.input", return_value=""):
                main.main()

        mock_report.generate_json_report.assert_called_once_with(ANALYSIS_DICT, SCORES_DICT)
        mock_report.generate_text_report.assert_not_called()
        mock_report.save_report.assert_called_once_with(
            '{"analysis": {}, "scores": {}}', "owner_repo_report.json"
        )

    @patch("main.menu")
    @patch("main.analyze_repository")
    @patch("main.report")
    def test_main_html_report_flow(self, mock_report, mock_analyze, mock_menu):
        mock_menu.get_user_choice.side_effect = ["Analyze a repository", "Exit"]
        mock_menu.prompt_repo_input.return_value = ("owner", "repo")
        mock_menu.prompt_report_format.return_value = "html"
        mock_menu.confirm_exit.return_value = True
        mock_analyze.return_value = (ANALYSIS_DICT, SCORES_DICT)
        mock_report.generate_html_report.return_value = "<!DOCTYPE html>"

        with patch("builtins.print"):
            with patch("builtins.input", return_value=""):
                main.main()

        mock_report.generate_html_report.assert_called_once_with(ANALYSIS_DICT, SCORES_DICT)
        mock_report.generate_text_report.assert_not_called()
        mock_report.generate_json_report.assert_not_called()
        mock_report.save_report.assert_called_once_with(
            "<!DOCTYPE html>", "owner_repo_report.html"
        )

    @patch("main.menu")
    @patch("main.analyze_repository")
    @patch("main.report")
    def test_main_text_report_filename(self, mock_report, mock_analyze, mock_menu):
        mock_menu.get_user_choice.side_effect = ["Analyze a repository", "Exit"]
        mock_menu.prompt_repo_input.return_value = ("owner", "repo")
        mock_menu.prompt_report_format.return_value = "text"
        mock_menu.confirm_exit.return_value = True
        mock_analyze.return_value = (ANALYSIS_DICT, SCORES_DICT)
        mock_report.generate_text_report.return_value = "report text"

        with patch("builtins.print"):
            with patch("builtins.input", return_value=""):
                main.main()

        mock_report.generate_json_report.assert_not_called()
        mock_report.save_report.assert_called_once_with(
            "report text", "owner_repo_report.txt"
        )

    @patch("main.menu")
    @patch("main.analyze_repository")
    @patch("main.report")
    def test_main_handles_save_permission_error(self, mock_report, mock_analyze, mock_menu):
        mock_menu.get_user_choice.side_effect = ["Analyze a repository", "Exit"]
        mock_menu.prompt_repo_input.return_value = ("owner", "repo")
        mock_menu.prompt_report_format.return_value = "text"
        mock_menu.confirm_exit.return_value = True
        mock_analyze.return_value = (ANALYSIS_DICT, SCORES_DICT)
        mock_report.generate_text_report.return_value = "report text"
        mock_report.save_report.side_effect = PermissionError("denied")

        with patch("builtins.print") as mock_print:
            with patch("builtins.input", return_value=""):
                main.main()

        self.assertTrue(
            any("cannot write owner_repo_report.txt" in str(c) for c in mock_print.call_args_list)
        )

    @patch("main.menu")
    @patch("main.analyze_repository")
    @patch("main.report")
    def test_main_handles_save_io_error(self, mock_report, mock_analyze, mock_menu):
        mock_menu.get_user_choice.side_effect = ["Analyze a repository", "Exit"]
        mock_menu.prompt_repo_input.return_value = ("owner", "repo")
        mock_menu.prompt_report_format.return_value = "text"
        mock_menu.confirm_exit.return_value = True
        mock_analyze.return_value = (ANALYSIS_DICT, SCORES_DICT)
        mock_report.generate_text_report.return_value = "report text"
        mock_report.save_report.side_effect = IOError("disk full")

        with patch("builtins.print") as mock_print:
            with patch("builtins.input", return_value=""):
                main.main()

        self.assertTrue(
            any("disk full" in str(c) for c in mock_print.call_args_list)
        )


if __name__ == "__main__":
    unittest.main()
