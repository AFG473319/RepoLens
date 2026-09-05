import io
import unittest
from unittest.mock import patch, MagicMock
import requests
import provider


def _mock_response(data, status_code=200, next_url=None, headers=None):
    """Build a fake requests.Response for tests."""
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = data
    response.links = {"next": {"url": next_url}} if next_url else {}
    response.headers = headers if headers is not None else {}
    return response


class TestGitLabHelpers(unittest.TestCase):
    def test_gitlab_project_path_encoding(self):
        self.assertEqual(
            provider._gitlab_project_path("gitlab-org", "gitlab"),
            "gitlab-org%2Fgitlab",
        )
        self.assertEqual(
            provider._gitlab_project_path("group/subgroup", "project"),
            "group%2Fsubgroup%2Fproject",
        )
        self.assertEqual(
            provider._gitlab_project_path("/owner/", "/repo/"),
            "owner%2Frepo",
        )

    def test_gitlab_reset_time(self):
        headers = {"RateLimit-Reset": "1672531199"}
        reset = provider._gitlab_reset_time(headers)
        self.assertIsNotNone(reset)
        self.assertIn("UTC", reset)

    def test_gitlab_reset_time_missing(self):
        self.assertIsNone(provider._gitlab_reset_time({}))
        self.assertIsNone(provider._gitlab_reset_time({"RateLimit-Reset": "invalid"}))

    def test_gitlab_retry_after_seconds(self):
        self.assertEqual(provider._gitlab_retry_after_seconds({"Retry-After": "45"}), 45)
        self.assertEqual(provider._gitlab_retry_after_seconds({"Retry-After": "0"}), 1)
        self.assertEqual(provider._gitlab_retry_after_seconds({"Retry-After": "999"}), 60)
        self.assertEqual(provider._gitlab_retry_after_seconds({}), 60)


class TestGitLabGetRepo(unittest.TestCase):
    @patch("provider.requests.get")
    def test_get_repo_gitlab_normalizes_data(self, mock_get):
        # First call: project metadata; second call: languages for primary language
        mock_meta = _mock_response({
            "name": "my-project",
            "description": "A sample project",
            "star_count": 42,
            "forks_count": 10,
        })
        mock_langs = _mock_response({
            "Python": 80.0,
            "HTML": 20.0,
        })
        mock_get.side_effect = [mock_meta, mock_langs]

        result = provider.get_repo("group", "my-project", platform="gitlab")

        self.assertEqual(result["name"], "my-project")
        self.assertEqual(result["description"], "A sample project")
        self.assertEqual(result["stargazers_count"], 42)
        self.assertEqual(result["stars"], 42)
        self.assertEqual(result["forks_count"], 10)
        self.assertEqual(result["language"], "Python")

    @patch("provider.requests.get")
    def test_get_repo_gitlab_with_api_key(self, mock_get):
        mock_meta = _mock_response({
            "name": "my-project",
            "star_count": 5,
            "forks_count": 2,
        })
        mock_langs = _mock_response({})
        mock_get.side_effect = [mock_meta, mock_langs]

        result = provider.get_repo("group", "my-project", api_key="gl_token", platform="gitlab")

        self.assertEqual(result["name"], "my-project")
        # Ensure PRIVATE-TOKEN header was sent
        call_headers = mock_get.call_args_list[0][1]["headers"]
        self.assertEqual(call_headers.get("PRIVATE-TOKEN"), "gl_token")


class TestGitLabGetCommits(unittest.TestCase):
    @patch("provider.requests.get")
    def test_get_commits_gitlab_normalizes_to_nested_structure(self, mock_get):
        mock_commits = _mock_response([
            {
                "id": "abc123",
                "author_name": "Alice Developer",
                "committed_date": "2024-01-15T12:00:00Z",
            },
            {
                "id": "def456",
                "committer_name": "Bob Reviewer",
                "authored_date": "2024-01-10T08:30:00Z",
            },
        ])
        mock_get.return_value = mock_commits

        commits, truncated = provider.get_commits("group", "repo", platform="gitlab")

        self.assertFalse(truncated)
        self.assertEqual(len(commits), 2)
        self.assertEqual(commits[0]["commit"]["author"]["name"], "Alice Developer")
        self.assertEqual(commits[0]["commit"]["author"]["date"], "2024-01-15T12:00:00Z")
        self.assertEqual(commits[1]["commit"]["author"]["name"], "Bob Reviewer")
        self.assertEqual(commits[1]["commit"]["author"]["date"], "2024-01-10T08:30:00Z")

    @patch("provider.requests.get")
    def test_get_commits_gitlab_empty_repo(self, mock_get):
        resp = _mock_response({}, status_code=404)
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(response=resp)
        mock_get.return_value = resp

        commits, truncated = provider.get_commits("group", "empty-repo", platform="gitlab")

        self.assertEqual(commits, [])
        self.assertFalse(truncated)


class TestGitLabGetContributors(unittest.TestCase):
    @patch("provider.requests.get")
    def test_get_contributors_gitlab_normalizes_structure(self, mock_get):
        mock_contribs = _mock_response([
            {"name": "Alice", "email": "alice@example.com", "commits": 50},
            {"name": "Bob", "email": "bob@example.com", "commits": 25},
        ])
        mock_get.return_value = mock_contribs

        contributors, truncated = provider.get_contributors("group", "repo", platform="gitlab")

        self.assertFalse(truncated)
        self.assertEqual(len(contributors), 2)
        self.assertEqual(contributors[0]["login"], "Alice")
        self.assertEqual(contributors[0]["contributions"], 50)
        self.assertEqual(contributors[1]["login"], "Bob")
        self.assertEqual(contributors[1]["contributions"], 25)


class TestGitLabGetLanguages(unittest.TestCase):
    @patch("provider.requests.get")
    def test_get_languages_gitlab_returns_dict(self, mock_get):
        mock_langs = _mock_response({"Python": 70.0, "JavaScript": 30.0})
        mock_get.return_value = mock_langs

        languages = provider.get_languages("group", "repo", platform="gitlab")

        self.assertEqual(languages, {"Python": 70.0, "JavaScript": 30.0})


class TestGitLabGetIssues(unittest.TestCase):
    @patch("provider.requests.get")
    def test_get_issues_gitlab_normalizes_opened_state(self, mock_get):
        mock_issues = _mock_response([
            {"id": 1, "title": "Bug A", "state": "opened"},
            {"id": 2, "title": "Bug B", "state": "closed"},
        ])
        mock_get.return_value = mock_issues

        issues, truncated = provider.get_issues("group", "repo", platform="gitlab")

        self.assertFalse(truncated)
        self.assertEqual(len(issues), 2)
        self.assertEqual(issues[0]["state"], "open")
        self.assertEqual(issues[1]["state"], "closed")


class TestGitLabRateLimiting(unittest.TestCase):
    @patch("provider.time.sleep")
    @patch("provider.requests.get")
    def test_fetch_gitlab_retries_on_429(self, mock_get, mock_sleep):
        resp_429 = _mock_response({}, status_code=429, headers={"Retry-After": "5"})
        resp_200 = _mock_response({"name": "success"}, status_code=200)
        mock_get.side_effect = [resp_429, resp_200]

        result = provider._fetch_gitlab("https://gitlab.com/api/v4/projects/test")

        self.assertEqual(result.status_code, 200)
        mock_sleep.assert_called_once_with(5)



class TestGitLabFetchGuards(unittest.TestCase):
    """F3/F5/F8: GitLab fetch guards parity with the GitHub path."""

    @patch("provider.requests.get")
    def test_fetch_gitlab_404_raises_actionable_error(self, mock_get):
        mock_get.return_value = _mock_response({}, status_code=404)
        with self.assertRaises(requests.exceptions.HTTPError) as ctx:
            provider._fetch_gitlab("https://gitlab.com/api/v4/projects/nope")
        self.assertIn("Make sure the project exists and you have access", str(ctx.exception))

    @patch("provider.requests.get")
    def test_fetch_gitlab_403_raises_actionable_error(self, mock_get):
        mock_get.return_value = _mock_response({}, status_code=403)
        with self.assertRaises(requests.exceptions.HTTPError) as ctx:
            provider._fetch_gitlab("https://gitlab.com/api/v4/projects/private")
        self.assertIn("Make sure you have access to the project", str(ctx.exception))
        self.assertIn("GITLAB_API_KEY", str(ctx.exception))

    @patch("provider.requests.get")
    def test_paginate_gitlab_maps_204_to_empty_list(self, mock_get):
        mock_get.return_value = _mock_response(None, status_code=204)
        items, truncated = provider._paginate_gitlab("group%2Fproj", "/repository/contributors")
        self.assertEqual(items, [])
        self.assertFalse(truncated)

    @patch("provider.requests.get")
    def test_paginate_gitlab_truncation_warning_decodes_path(self, mock_get):
        page = _mock_response([{"id": 1}], next_url="https://gitlab.com/api/v4/projects/g%2Fp/x?page=2")
        mock_get.return_value = page
        with patch.object(provider, "MAX_PAGES", 1):
            with patch("sys.stderr", new=io.StringIO()) as fake_err:
                _, truncated = provider._paginate_gitlab("g%2Fp", "/x")
        self.assertTrue(truncated)
        self.assertIn("g/p/x", fake_err.getvalue())
        self.assertNotIn("g%2Fp", fake_err.getvalue())


class TestGitLabGetRepoLanguages(unittest.TestCase):
    """F1/F2: get_repo owns the single languages fetch and signals failure."""

    @patch("provider.get_languages")
    @patch("provider.requests.get")
    def test_get_repo_gitlab_includes_languages_map(self, mock_get, mock_get_languages):
        mock_get.return_value = _mock_response({"name": "proj", "star_count": 1, "forks_count": 1})
        mock_get_languages.return_value = {"Python": 80.0, "HTML": 20.0}

        result = provider.get_repo("group", "proj", platform="gitlab")

        self.assertEqual(result["languages"], {"Python": 80.0, "HTML": 20.0})
        self.assertEqual(result["language"], "Python")

    @patch("provider.get_languages")
    @patch("provider.requests.get")
    def test_get_repo_gitlab_language_failure_sets_none_and_warns(self, mock_get, mock_get_languages):
        mock_get.return_value = _mock_response({"name": "proj"})
        mock_get_languages.side_effect = requests.exceptions.ConnectionError("boom")

        with patch("sys.stderr", new=io.StringIO()) as fake_err:
            result = provider.get_repo("group", "proj", platform="gitlab")

        self.assertIsNone(result["languages"])
        self.assertIsNone(result["language"])
        self.assertIn("could not fetch language breakdown", fake_err.getvalue())

    @patch("provider.requests.get")
    def test_get_issues_gitlab_requests_scopeless_url(self, mock_get):
        mock_get.return_value = _mock_response([])
        provider.get_issues("group", "repo", platform="gitlab")
        url = mock_get.call_args[0][0]
        self.assertIn("/issues?per_page=100", url)
        self.assertNotIn("scope=", url)


if __name__ == "__main__":
    unittest.main()
