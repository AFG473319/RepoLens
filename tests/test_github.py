import sys
import unittest
from unittest.mock import patch, MagicMock
import requests
import github


def _mock_response(data, next_url=None):
    """Build a fake requests.Response for tests."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = data
    response.links = {"next": {"url": next_url}} if next_url else {}
    return response


class TestGetRepo(unittest.TestCase):
    @patch("github.requests.get")
    def test_get_repo_returns_json(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name": "test-repo"}
        mock_get.return_value = mock_response

        result = github.get_repo("owner", "repo")
        self.assertEqual(result, {"name": "test-repo"})
        mock_get.assert_called_once_with(
            "https://api.github.com/repos/owner/repo", headers={}, timeout=10
        )

    @patch("github.requests.get")
    def test_get_repo_with_endpoint(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        mock_get.return_value = mock_response

        result = github.get_repo("owner", "repo", endpoint="/commits")
        self.assertEqual(result, [])
        mock_get.assert_called_once_with(
            "https://api.github.com/repos/owner/repo/commits", headers={}, timeout=10
        )

    @patch("github.requests.get")
    def test_get_repo_raises_on_bad_status(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("404")
        mock_get.return_value = mock_response

        with self.assertRaises(Exception):
            github.get_repo("owner", "repo")


class TestFetchTypeValidation(unittest.TestCase):
    @patch("github.requests.get")
    def test_fetch_returns_response_when_type_matches(self, mock_get):
        response = _mock_response({"Python": 1000})
        mock_get.return_value = response

        result = github._fetch(
            "https://api.github.com/repos/owner/repo/languages",
            expected_type=dict,
        )

        self.assertIs(result, response)

    @patch("github.requests.get")
    def test_fetch_raises_type_error_when_type_mismatches(self, mock_get):
        mock_get.return_value = _mock_response([])

        with self.assertRaises(TypeError):
            github._fetch(
                "https://api.github.com/repos/owner/repo/languages",
                expected_type=dict,
            )


class TestGetRetries(unittest.TestCase):
    @patch("github.time.sleep")
    @patch("github.requests.get")
    def test_get_repo_retries_on_timeout(self, mock_get, mock_sleep):
        mock_get.side_effect = [
            requests.exceptions.Timeout(),
            _mock_response({"name": "test-repo"}),
        ]

        result = github.get_repo("owner", "repo")

        self.assertEqual(result, {"name": "test-repo"})
        self.assertEqual(mock_get.call_count, 2)

    @patch("github.time.sleep")
    @patch("github.requests.get")
    def test_get_repo_retries_on_connection_error(self, mock_get, mock_sleep):
        mock_get.side_effect = [
            requests.exceptions.ConnectionError(),
            _mock_response({"name": "test-repo"}),
        ]

        result = github.get_repo("owner", "repo")

        self.assertEqual(result, {"name": "test-repo"})
        self.assertEqual(mock_get.call_count, 2)

    @patch("github.time.sleep")
    @patch("github.requests.get")
    def test_get_repo_raises_after_retries_exhausted(self, mock_get, mock_sleep):
        mock_get.side_effect = [requests.exceptions.Timeout()] * 4

        with self.assertRaises(requests.exceptions.Timeout):
            github.get_repo("owner", "repo")

        self.assertEqual(mock_get.call_count, 4)

    @patch("github.time.sleep")
    @patch("github.requests.get")
    def test_get_repo_retries_on_429_then_succeeds(self, mock_get, mock_sleep):
        rate_limited = _mock_response({"message": "rate limited"})
        rate_limited.status_code = 429
        rate_limited.headers = {"Retry-After": "1"}
        mock_get.side_effect = [rate_limited, _mock_response({"name": "test-repo"})]

        result = github.get_repo("owner", "repo")

        self.assertEqual(result, {"name": "test-repo"})
        self.assertEqual(mock_get.call_count, 2)


class TestValidateType(unittest.TestCase):
    def test_passes_data_through_when_type_matches(self):
        data = [{"n": 1}]

        self.assertIs(github._validate_type(data, list), data)

    def test_raises_type_error_on_mismatch(self):
        with self.assertRaises(TypeError) as ctx:
            github._validate_type([], dict)

        self.assertIn("Expected dict response from API, got list", str(ctx.exception))


class TestPaginate(unittest.TestCase):
    @patch("github._fetch")
    def test_fetches_all_pages(self, mock_get):
        mock_get.side_effect = [
            _mock_response(
                [{"n": 1}, {"n": 2}],
                next_url="https://api.github.com/repos/owner/repo/commits?per_page=100&page=2",
            ),
            _mock_response([{"n": 3}]),
        ]

        result = github._paginate("owner", "repo", "/commits")

        self.assertEqual(result, [{"n": 1}, {"n": 2}, {"n": 3}])
        self.assertEqual(mock_get.call_count, 2)
        mock_get.assert_any_call(
            "https://api.github.com/repos/owner/repo/commits?per_page=100",
            api_key=None,
            expected_type=list,
        )
        mock_get.assert_any_call(
            "https://api.github.com/repos/owner/repo/commits?per_page=100&page=2",
            api_key=None,
            expected_type=list,
        )

    @patch("github._fetch")
    def test_single_page(self, mock_get):
        mock_get.return_value = _mock_response([{"n": 1}])

        result = github._paginate("owner", "repo", "/commits")

        self.assertEqual(result, [{"n": 1}])
        mock_get.assert_called_once()

    @patch("github._fetch")
    def test_appends_to_existing_query_string(self, mock_get):
        mock_get.return_value = _mock_response([])

        github._paginate("owner", "repo", "/issues?state=all")

        mock_get.assert_called_once_with(
            "https://api.github.com/repos/owner/repo/issues?state=all&per_page=100",
            api_key=None,
            expected_type=list,
        )

    @patch("builtins.print")
    @patch("github._fetch")
    def test_stops_at_page_cap_and_warns(self, mock_get, mock_print):
        mock_get.return_value = _mock_response(
            [{"n": 1}], next_url="https://api.github.com/repos/owner/repo/commits?per_page=100&page=2"
        )

        result = github._paginate("owner", "repo", "/commits")

        self.assertEqual(len(result), github.MAX_PAGES)
        self.assertEqual(mock_get.call_count, github.MAX_PAGES)
        mock_print.assert_called_once()
        self.assertIn("approximate", mock_print.call_args[0][0])
        self.assertEqual(mock_print.call_args[1].get("file"), sys.stderr)

    @patch("github.requests.get")
    def test_raises_type_error_if_not_list(self, mock_get):
        mock_get.return_value = _mock_response({"error": "not found"})

        with self.assertRaises(TypeError):
            github._paginate("owner", "repo", "/commits")


class TestGetCommits(unittest.TestCase):
    @patch("github._paginate")
    def test_get_commits_returns_list(self, mock_paginate):
        mock_paginate.return_value = [
            {"commit": {"author": {"name": "Alice"}}}
        ]

        result = github.get_commits("owner", "repo")

        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        mock_paginate.assert_called_once_with("owner", "repo", "/commits", api_key=None)

    @patch("github._paginate")
    def test_get_commits_raises_type_error_if_not_list(self, mock_paginate):
        mock_paginate.side_effect = TypeError("Expected list response from API, got dict")

        with self.assertRaises(TypeError):
            github.get_commits("owner", "repo")


class TestGetContributors(unittest.TestCase):
    @patch("github._paginate")
    def test_get_contributors_returns_list(self, mock_paginate):
        mock_paginate.return_value = [
            {"login": "Alice", "contributions": 5}
        ]

        result = github.get_contributors("owner", "repo")
        self.assertIsInstance(result, list)
        self.assertEqual(result[0]["login"], "Alice")
        mock_paginate.assert_called_once_with(
            "owner", "repo", "/contributors", api_key=None
        )

    @patch("github._paginate")
    def test_get_contributors_raises_type_error_if_not_list(self, mock_paginate):
        mock_paginate.side_effect = TypeError("Expected list response from API, got dict")

        with self.assertRaises(TypeError):
            github.get_contributors("owner", "repo")


class TestGetLanguages(unittest.TestCase):
    @patch("github._fetch")
    def test_get_languages_returns_dict(self, mock_fetch):
        mock_fetch.return_value = _mock_response(
            {"Python": 1000, "JavaScript": 500}
        )

        result = github.get_languages("owner", "repo")
        self.assertIsInstance(result, dict)
        self.assertEqual(result["Python"], 1000)
        mock_fetch.assert_called_once_with(
            "https://api.github.com/repos/owner/repo/languages",
            api_key=None,
            expected_type=dict,
        )

    @patch("github.requests.get")
    def test_get_languages_raises_type_error_if_not_dict(self, mock_get):
        mock_get.return_value = _mock_response([])

        with self.assertRaises(TypeError):
            github.get_languages("owner", "repo")


class TestGetIssues(unittest.TestCase):
    @patch("github._paginate")
    def test_get_issues_returns_list(self, mock_paginate):
        mock_paginate.return_value = [
            {"number": 1, "state": "open"},
            {"number": 2, "state": "closed"},
        ]

        result = github.get_issues("owner", "repo")
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 2)
        mock_paginate.assert_called_once_with(
            "owner", "repo", "/issues?state=all", api_key=None
        )

    @patch("github._paginate")
    def test_get_issues_raises_type_error_if_not_list(self, mock_paginate):
        mock_paginate.side_effect = TypeError("Expected list response from API, got dict")

        with self.assertRaises(TypeError):
            github.get_issues("owner", "repo")


if __name__ == "__main__":
    unittest.main()
