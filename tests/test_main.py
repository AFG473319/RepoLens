import unittest
from unittest.mock import patch, MagicMock
import main


class TestAnalyzeRepository(unittest.TestCase):
    @patch("main.github")
    @patch("main.analyzer")
    @patch("main.scoring")
    def test_analyze_repository_pipeline(self, mock_scoring, mock_analyzer, mock_github):
        mock_github.get_repo.return_value = {"name": "test-repo"}
        mock_github.get_commits.return_value = [
            {"commit": {"author": {"name": "Alice", "date": "2024-06-15"}}}
        ]
        mock_github.get_contributors.return_value = [
            {"login": "Alice", "contributions": 10}
        ]
        mock_github.get_languages.return_value = {"Python": 1000}
        mock_github.get_issues.return_value = [
            {"state": "open"}, {"state": "closed"}
        ]

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

        mock_analyze.return_value = (
            {
                "repo": {},
                "commits": {},
                "contributors": {},
                "languages": {},
                "issues": {},
            },
            {
                "health_score": 85.0,
                "activity_score": 70.0,
                "community_score": 60.0,
                "maintainability_score": 90.0,
                "grade": "B",
            },
        )

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
        mock_analyze.side_effect = Exception("API Error")

        with patch("builtins.print"):
            with patch("builtins.input", return_value=""):
                main.main()

        mock_analyze.assert_called_once_with("owner", "repo")


if __name__ == "__main__":
    unittest.main()
