import unittest
from unittest.mock import patch, MagicMock
import github


class TestGetRepo(unittest.TestCase):
    @patch("github.requests.get")
    def test_get_repo_returns_json(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {"name": "test-repo"}
        mock_get.return_value = mock_response

        result = github.getRepo("owner", "repo")
        self.assertEqual(result, {"name": "test-repo"})
        mock_get.assert_called_once_with(
            "https://api.github.com/repos/owner/repo"
        )

    @patch("github.requests.get")
    def test_get_repo_with_endpoint(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        result = github.getRepo("owner", "repo", endpoint="/commits")
        self.assertEqual(result, [])
        mock_get.assert_called_once_with(
            "https://api.github.com/repos/owner/repo/commits"
        )

    @patch("github.requests.get")
    def test_get_repo_raises_on_bad_status(self, mock_get):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("404")
        mock_get.return_value = mock_response

        with self.assertRaises(Exception):
            github.getRepo("owner", "repo")


class TestGetCommits(unittest.TestCase):
    @patch("github.getRepo")
    def test_get_commits_returns_list(self, mock_get_repo):
        mock_get_repo.return_value = [
            {"commit": {"author": {"name": "Alice"}}}
        ]

        result = github.getCommits("owner", "repo")
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        mock_get_repo.assert_called_once_with("owner", "repo", endpoint="/commits")

    @patch("github.getRepo")
    def test_get_commits_raises_type_error_if_not_list(self, mock_get_repo):
        mock_get_repo.return_value = {"error": "not found"}

        with self.assertRaises(TypeError):
            github.getCommits("owner", "repo")


class TestGetContributors(unittest.TestCase):
    @patch("github.getRepo")
    def test_get_contributors_returns_list(self, mock_get_repo):
        mock_get_repo.return_value = [
            {"login": "Alice", "contributions": 5}
        ]

        result = github.getContributors("owner", "repo")
        self.assertIsInstance(result, list)
        self.assertEqual(result[0]["login"], "Alice")
        mock_get_repo.assert_called_once_with(
            "owner", "repo", "/contributors"
        )

    @patch("github.getRepo")
    def test_get_contributors_raises_type_error_if_not_list(self, mock_get_repo):
        mock_get_repo.return_value = {"error": "not found"}

        with self.assertRaises(TypeError):
            github.getContributors("owner", "repo")


class TestGetLanguages(unittest.TestCase):
    @patch("github.getRepo")
    def test_get_languages_returns_dict(self, mock_get_repo):
        mock_get_repo.return_value = {"Python": 1000, "JavaScript": 500}

        result = github.getLanguages("owner", "repo")
        self.assertIsInstance(result, dict)
        self.assertEqual(result["Python"], 1000)
        mock_get_repo.assert_called_once_with(
            "owner", "repo", "/languages"
        )

    @patch("github.getRepo")
    def test_get_languages_raises_type_error_if_not_dict(self, mock_get_repo):
        mock_get_repo.return_value = []

        with self.assertRaises(TypeError):
            github.getLanguages("owner", "repo")


class TestGetIssues(unittest.TestCase):
    @patch("github.getRepo")
    def test_get_issues_returns_list(self, mock_get_repo):
        mock_get_repo.return_value = [
            {"number": 1, "state": "open"},
            {"number": 2, "state": "closed"},
        ]

        result = github.getIssues("owner", "repo")
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        mock_get_repo.assert_called_once_with(
            "owner", "repo", "/issues"
        )

    @patch("github.getRepo")
    def test_get_issues_raises_type_error_if_not_list(self, mock_get_repo):
        mock_get_repo.return_value = {"error": "not found"}

        with self.assertRaises(TypeError):
            github.getIssues("owner", "repo")


if __name__ == "__main__":
    unittest.main()
