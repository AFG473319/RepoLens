import sys
import unittest
from unittest.mock import patch, MagicMock

import requests

import provider as github


def _mock_response(data, next_url=None):
    """Build a fake requests.Response for tests."""
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = data
    response.links = {"next": {"url": next_url}} if next_url else {}
    return response


def _status_response(status_code, data=None, headers=None):
    """Build a fake requests.Response with an arbitrary status code."""
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = data if data is not None else {}
    response.headers = headers if headers is not None else {}
    return response


class TestGetRepo(unittest.TestCase):
    @patch("provider.requests.get")
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

    @patch("provider.requests.get")
    def test_get_repo_with_endpoint(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"name": "test-repo"}
        mock_get.return_value = mock_response

        result = github.get_repo("owner", "repo", endpoint="/commits")
        self.assertEqual(result, {"name": "test-repo"})
        mock_get.assert_called_once_with(
            "https://api.github.com/repos/owner/repo/commits", headers={}, timeout=10
        )

    @patch("provider.requests.get")
    def test_get_repo_raises_on_bad_status(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("404")
        mock_get.return_value = mock_response

        with self.assertRaises(Exception):
            github.get_repo("owner", "repo")

    @patch("provider.requests.get")
    def test_get_repo_passes_api_key_header(self, mock_get):
        mock_get.return_value = _mock_response({"name": "test-repo"})

        result = github.get_repo("owner", "repo", api_key="secret")

        self.assertEqual(result, {"name": "test-repo"})
        mock_get.assert_called_once_with(
            "https://api.github.com/repos/owner/repo",
            headers={"Authorization": "token secret"},
            timeout=10,
        )


class TestFetchTypeValidation(unittest.TestCase):
    @patch("provider.requests.get")
    def test_fetch_returns_response_when_type_matches(self, mock_get):
        response = _mock_response({"Python": 1000})
        mock_get.return_value = response

        result = github._fetch(
            "https://api.github.com/repos/owner/repo/languages",
            expected_type=dict,
        )

        self.assertIs(result, response)

    @patch("provider.requests.get")
    def test_fetch_raises_type_error_when_type_mismatches(self, mock_get):
        mock_get.return_value = _mock_response([])

        with self.assertRaises(TypeError):
            github._fetch(
                "https://api.github.com/repos/owner/repo/languages",
                expected_type=dict,
            )


class TestGetRetries(unittest.TestCase):
    @patch("provider.time.sleep")
    @patch("provider.requests.get")
    def test_get_repo_retries_on_timeout(self, mock_get, mock_sleep):
        mock_get.side_effect = [
            requests.exceptions.Timeout(),
            _mock_response({"name": "test-repo"}),
        ]

        result = github.get_repo("owner", "repo")

        self.assertEqual(result, {"name": "test-repo"})
        self.assertEqual(mock_get.call_count, 2)

    @patch("provider.time.sleep")
    @patch("provider.requests.get")
    def test_get_repo_retries_on_connection_error(self, mock_get, mock_sleep):
        mock_get.side_effect = [
            requests.exceptions.ConnectionError(),
            _mock_response({"name": "test-repo"}),
        ]

        result = github.get_repo("owner", "repo")

        self.assertEqual(result, {"name": "test-repo"})
        self.assertEqual(mock_get.call_count, 2)

    @patch("provider.time.sleep")
    @patch("provider.requests.get")
    def test_get_repo_raises_after_retries_exhausted(self, mock_get, mock_sleep):
        mock_get.side_effect = [requests.exceptions.Timeout()] * 4

        with self.assertRaises(requests.exceptions.Timeout):
            github.get_repo("owner", "repo")

        self.assertEqual(mock_get.call_count, 4)

    @patch("provider.time.sleep")
    @patch("provider.requests.get")
    def test_get_repo_retries_on_429_then_succeeds(self, mock_get, mock_sleep):
        rate_limited = _mock_response({"message": "rate limited"})
        rate_limited.status_code = 429
        rate_limited.headers = {"Retry-After": "1"}
        mock_get.side_effect = [rate_limited, _mock_response({"name": "test-repo"})]

        result = github.get_repo("owner", "repo")

        self.assertEqual(result, {"name": "test-repo"})
        self.assertEqual(mock_get.call_count, 2)

    @patch("provider.time.sleep")
    @patch("provider.requests.get")
    def test_retries_on_500_then_succeeds(self, mock_get, mock_sleep):
        mock_get.side_effect = [
            _status_response(500),
            _status_response(500),
            _status_response(500),
            _mock_response({"name": "test-repo"}),
        ]

        result = github.get_repo("owner", "repo")

        self.assertEqual(result, {"name": "test-repo"})
        self.assertEqual(mock_get.call_count, 4)
        self.assertEqual([c[0][0] for c in mock_sleep.call_args_list], [1, 2, 4])

    @patch("provider.time.sleep")
    @patch("provider.requests.get")
    def test_raises_http_error_after_500_retries_exhausted(self, mock_get, mock_sleep):
        responses = []
        for _ in range(4):
            response = _status_response(500)
            response.raise_for_status.side_effect = requests.exceptions.HTTPError("500")
            responses.append(response)
        mock_get.side_effect = responses

        with self.assertRaises(requests.exceptions.HTTPError):
            github.get_repo("owner", "repo")

        self.assertEqual(mock_get.call_count, 4)

    @patch("provider.time.sleep")
    @patch("provider.requests.get")
    def test_429_without_retry_after_defaults_to_sixty_seconds(
        self, mock_get, mock_sleep
    ):
        rate_limited = _mock_response({"message": "rate limited"})
        rate_limited.status_code = 429
        rate_limited.headers = {}
        mock_get.side_effect = [rate_limited, _mock_response({"name": "test-repo"})]

        result = github.get_repo("owner", "repo")

        self.assertEqual(result, {"name": "test-repo"})
        mock_sleep.assert_called_once_with(60)

    @patch("provider.time.sleep")
    @patch("provider.requests.get")
    def test_raises_after_429_retries_exhausted(self, mock_get, mock_sleep):
        responses = []
        for _ in range(4):
            response = _mock_response({"message": "rate limited"})
            response.status_code = 429
            response.headers = {"Retry-After": "1"}
            response.raise_for_status.side_effect = requests.exceptions.HTTPError("429")
            responses.append(response)
        mock_get.side_effect = responses

        with self.assertRaises(requests.exceptions.HTTPError):
            github.get_repo("owner", "repo")

        self.assertEqual(mock_get.call_count, 4)

    @patch("provider.time.sleep")
    @patch("provider.requests.get")
    def test_connection_error_backoff_increments(self, mock_get, mock_sleep):
        mock_get.side_effect = [
            requests.exceptions.ConnectionError(),
            requests.exceptions.ConnectionError(),
            _mock_response({"name": "test-repo"}),
        ]

        result = github.get_repo("owner", "repo")

        self.assertEqual(result, {"name": "test-repo"})
        self.assertEqual([c[0][0] for c in mock_sleep.call_args_list], [1, 2])

    @patch("provider.time.sleep")
    @patch("provider.requests.get")
    def test_no_retry_on_404(self, mock_get, mock_sleep):
        response = _status_response(404)
        response.raise_for_status.side_effect = requests.exceptions.HTTPError("404")
        mock_get.return_value = response

        with self.assertRaises(requests.exceptions.HTTPError):
            github.get_repo("owner", "repo")

        self.assertEqual(mock_get.call_count, 1)
        mock_sleep.assert_not_called()


class TestRetryAfterSeconds(unittest.TestCase):
    def test_missing_header_returns_default(self):
        self.assertEqual(github._retry_after_seconds({}), 60)

    def test_empty_header_returns_default(self):
        self.assertEqual(github._retry_after_seconds({"Retry-After": ""}), 60)

    def test_valid_seconds_parsed(self):
        self.assertEqual(github._retry_after_seconds({"Retry-After": "5"}), 5)

    def test_large_value_falls_back_to_default(self):
        self.assertEqual(github._retry_after_seconds({"Retry-After": "150"}), 60)

    def test_value_at_cap_is_honored(self):
        self.assertEqual(github._retry_after_seconds({"Retry-After": "100"}), 100)

    def test_zero_clamped_to_one_second_floor(self):
        self.assertEqual(github._retry_after_seconds({"Retry-After": "0"}), 1)

    def test_negative_clamped_to_one_second_floor(self):
        self.assertEqual(github._retry_after_seconds({"Retry-After": "-5"}), 1)

    def test_garbage_returns_default(self):
        self.assertEqual(
            github._retry_after_seconds({"Retry-After": "garbage"}), 60
        )

    def test_http_date_falls_back_to_default(self):
        self.assertEqual(
            github._retry_after_seconds(
                {"Retry-After": "Wed, 21 Oct 2015 07:28:00 GMT"}
            ),
            60,
        )

    def test_custom_default_respected(self):
        self.assertEqual(github._retry_after_seconds({}, default=3), 3)
        self.assertEqual(
            github._retry_after_seconds({"Retry-After": "garbage"}, default=3),
            3,
        )
        self.assertEqual(
            github._retry_after_seconds({"Retry-After": "10"}, default=3), 10
        )


class TestRateLimited(unittest.TestCase):
    def _response(self, status_code, headers=None):
        response = MagicMock()
        response.status_code = status_code
        response.headers = headers if headers is not None else {}
        return response

    def test_429_is_always_rate_limited(self):
        self.assertTrue(github._rate_limited(self._response(429)))
        self.assertTrue(
            github._rate_limited(self._response(429, {"Retry-After": "1"}))
        )

    def test_403_with_retry_after_is_secondary_limit(self):
        self.assertTrue(
            github._rate_limited(self._response(403, {"Retry-After": "30"}))
        )

    def test_403_with_exhausted_primary_limit(self):
        self.assertTrue(
            github._rate_limited(
                self._response(403, {"x-ratelimit-remaining": "0"})
            )
        )

    def test_plain_403_is_a_permission_error_not_a_rate_limit(self):
        self.assertFalse(github._rate_limited(self._response(403)))

    def test_other_statuses_are_not_rate_limited(self):
        for status in (200, 204, 404, 500):
            self.assertFalse(github._rate_limited(self._response(status)))


class TestResetTime(unittest.TestCase):
    def test_missing_header_returns_none(self):
        self.assertIsNone(github._reset_time({}))

    def test_valid_epoch_formats_as_utc_clock_time(self):
        # 2025-01-01T00:00:00Z as epoch seconds.
        self.assertEqual(github._reset_time({"x-ratelimit-reset": "1735689600"}),
                         "00:00 UTC")

    def test_garbage_returns_none(self):
        self.assertIsNone(github._reset_time({"x-ratelimit-reset": "soon"}))


class TestRateLimitHandling(unittest.TestCase):
    @patch("provider.time.sleep")
    @patch("provider.requests.get")
    def test_403_primary_limit_raises_immediately_without_sleeping(
        self, mock_get, mock_sleep
    ):
        exhausted = _status_response(403, headers={"x-ratelimit-remaining": "0"})
        mock_get.return_value = exhausted

        with self.assertRaises(requests.exceptions.HTTPError) as ctx:
            github.get_repo("owner", "repo")

        self.assertIn("rate limit exceeded", str(ctx.exception))
        self.assertEqual(mock_get.call_count, 1)
        mock_sleep.assert_not_called()

    @patch("provider.time.sleep")
    @patch("provider.requests.get")
    def test_403_primary_limit_message_includes_reset_time(
        self, mock_get, mock_sleep
    ):
        exhausted = _status_response(
            403,
            headers={
                "x-ratelimit-remaining": "0",
                "x-ratelimit-reset": "1735689600",
            },
        )
        mock_get.return_value = exhausted

        with self.assertRaises(requests.exceptions.HTTPError) as ctx:
            github.get_repo("owner", "repo")

        self.assertIn("resets at 00:00 UTC", str(ctx.exception))

    @patch("provider.time.sleep")
    @patch("provider.requests.get")
    def test_403_with_retry_after_is_retried_then_succeeds(
        self, mock_get, mock_sleep
    ):
        secondary = _status_response(403, headers={"Retry-After": "2"})
        mock_get.side_effect = [secondary, _mock_response({"name": "test-repo"})]

        result = github.get_repo("owner", "repo")

        self.assertEqual(result, {"name": "test-repo"})
        self.assertEqual(mock_get.call_count, 2)
        mock_sleep.assert_called_once_with(2)

    @patch("provider.time.sleep")
    @patch("provider.requests.get")
    def test_403_secondary_limit_backoff_escalates(self, mock_get, mock_sleep):
        responses = [
            _status_response(403, headers={"Retry-After": "10"})
            for _ in range(3)
        ] + [_mock_response({"name": "test-repo"})]
        mock_get.side_effect = responses

        result = github.get_repo("owner", "repo")

        self.assertEqual(result, {"name": "test-repo"})
        self.assertEqual([c[0][0] for c in mock_sleep.call_args_list], [10, 20, 40])

    @patch("provider.time.sleep")
    @patch("provider.requests.get")
    def test_plain_403_is_raised_as_is_without_retry(self, mock_get, mock_sleep):
        forbidden = _status_response(403)
        forbidden.raise_for_status.side_effect = requests.exceptions.HTTPError("403")
        mock_get.return_value = forbidden

        with self.assertRaises(requests.exceptions.HTTPError):
            github.get_repo("owner", "repo")

        self.assertEqual(mock_get.call_count, 1)
        mock_sleep.assert_not_called()

    @patch("provider.time.sleep")
    @patch("provider.requests.get")
    def test_exhausted_secondary_limit_message_mentions_api_key(
        self, mock_get, mock_sleep
    ):
        secondary = _status_response(429, headers={"Retry-After": "1"})
        mock_get.return_value = secondary

        with self.assertRaises(requests.exceptions.HTTPError) as ctx:
            github.get_repo("owner", "repo", api_key="secret")

        self.assertIn("Your API key is rate limited", str(ctx.exception))
        self.assertEqual(mock_get.call_count, 4)


class TestValidateType(unittest.TestCase):
    def test_passes_data_through_when_type_matches(self):
        data = [{"n": 1}]

        self.assertIs(github._validate_type(data, list), data)

    def test_passes_dict_through(self):
        data = {"n": 1}

        self.assertIs(github._validate_type(data, dict), data)

    def test_raises_type_error_on_mismatch(self):
        with self.assertRaises(TypeError) as ctx:
            github._validate_type([], dict)

        self.assertIn("Expected dict response from API, got list", str(ctx.exception))

    def test_raises_type_error_message_for_dict_vs_list(self):
        with self.assertRaises(TypeError) as ctx:
            github._validate_type({}, list)

        self.assertIn("Expected list response from API, got dict", str(ctx.exception))


class TestPaginate(unittest.TestCase):
    @patch("provider._fetch")
    def test_fetches_all_pages(self, mock_get):
        mock_get.side_effect = [
            _mock_response(
                [{"n": 1}, {"n": 2}],
                next_url="https://api.github.com/repos/owner/repo/commits?per_page=100&page=2",
            ),
            _mock_response([{"n": 3}]),
        ]

        result, truncated = github._paginate("owner", "repo", "/commits")

        self.assertEqual(result, [{"n": 1}, {"n": 2}, {"n": 3}])
        self.assertFalse(truncated)
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

    @patch("provider._fetch")
    def test_single_page(self, mock_get):
        mock_get.return_value = _mock_response([{"n": 1}])

        result, truncated = github._paginate("owner", "repo", "/commits")

        self.assertEqual(result, [{"n": 1}])
        self.assertFalse(truncated)
        mock_get.assert_called_once()

    @patch("provider._fetch")
    def test_empty_first_page(self, mock_get):
        mock_get.return_value = _mock_response([])

        result, truncated = github._paginate("owner", "repo", "/commits")

        self.assertEqual(result, [])
        self.assertFalse(truncated)

    @patch("provider._fetch")
    def test_appends_to_existing_query_string(self, mock_get):
        mock_get.return_value = _mock_response([])

        github._paginate("owner", "repo", "/issues?state=all")

        mock_get.assert_called_once_with(
            "https://api.github.com/repos/owner/repo/issues?state=all&per_page=100",
            api_key=None,
            expected_type=list,
        )

    @patch("provider._fetch")
    def test_passes_api_key_through(self, mock_get):
        mock_get.return_value = _mock_response([])

        github._paginate("owner", "repo", "/commits", api_key="secret")

        mock_get.assert_called_once_with(
            "https://api.github.com/repos/owner/repo/commits?per_page=100",
            api_key="secret",
            expected_type=list,
        )

    @patch("builtins.print")
    @patch("provider._fetch")
    def test_stops_at_page_cap_and_warns(self, mock_get, mock_print):
        mock_get.return_value = _mock_response(
            [{"n": 1}],
            next_url="https://api.github.com/repos/owner/repo/commits?per_page=100&page=2",
        )

        result, truncated = github._paginate("owner", "repo", "/commits")

        self.assertEqual(len(result), github.MAX_PAGES)
        self.assertTrue(truncated)
        self.assertEqual(mock_get.call_count, github.MAX_PAGES)
        mock_print.assert_called_once()
        self.assertIn("approximate", mock_print.call_args[0][0])
        self.assertEqual(mock_print.call_args[1].get("file"), sys.stderr)

    @patch("builtins.print")
    @patch("provider._fetch")
    def test_no_warning_when_all_pages_fetched(self, mock_get, mock_print):
        mock_get.side_effect = [
            _mock_response([{"n": 1}], next_url="https://example.com/page=2"),
            _mock_response([{"n": 2}]),
        ]

        result, truncated = github._paginate("owner", "repo", "/commits")

        self.assertFalse(truncated)
        mock_print.assert_not_called()

    @patch("builtins.print")
    @patch("provider._fetch")
    def test_exact_page_cap_no_warning(self, mock_get, mock_print):
        responses = []
        for i in range(github.MAX_PAGES):
            next_url = "https://example.com/page=2" if i < github.MAX_PAGES - 1 else None
            responses.append(_mock_response([{"n": i}], next_url=next_url))
        mock_get.side_effect = responses

        result, truncated = github._paginate("owner", "repo", "/commits")

        self.assertEqual(len(result), github.MAX_PAGES)
        self.assertFalse(truncated)
        mock_print.assert_not_called()

    @patch("provider.requests.get")
    def test_raises_type_error_if_not_list(self, mock_get):
        mock_get.return_value = _mock_response({"error": "not found"})

        with self.assertRaises(TypeError):
            github._paginate("owner", "repo", "/commits")

    @patch("provider._fetch")
    def test_returns_empty_list_on_204_empty_repository(self, mock_fetch):
        empty = MagicMock()
        empty.status_code = 204
        empty.links = {}
        mock_fetch.return_value = empty

        result, truncated = github._paginate("owner", "repo", "/contributors")

        self.assertEqual(result, [])
        self.assertFalse(truncated)
        mock_fetch.assert_called_once()

    @patch("builtins.print")
    @patch("provider._fetch")
    def test_truncated_flag_true_when_page_cap_hit(self, mock_get, mock_print):
        mock_get.return_value = _mock_response(
            [{"n": 1}],
            next_url="https://api.github.com/repos/owner/repo/commits?per_page=100&page=2",
        )

        _result, truncated = github._paginate("owner", "repo", "/commits")

        self.assertTrue(truncated)

    @patch("provider._fetch")
    def test_truncated_flag_false_when_all_pages_fetched(self, mock_get):
        mock_get.side_effect = [
            _mock_response([{"n": 1}], next_url="https://example.com/page=2"),
            _mock_response([{"n": 2}]),
        ]

        _result, truncated = github._paginate("owner", "repo", "/commits")

        self.assertFalse(truncated)


class TestGetCommits(unittest.TestCase):
    @patch("provider._paginate")
    def test_get_commits_returns_tuple(self, mock_paginate):
        commits = [{"commit": {"author": {"name": "Alice"}}}]
        mock_paginate.return_value = (commits, False)

        result, truncated = github.get_commits("owner", "repo")

        self.assertIsInstance(result, list)
        self.assertFalse(truncated)
        self.assertEqual(len(result), 1)
        mock_paginate.assert_called_once_with("owner", "repo", "/commits", api_key=None)

    @patch("provider._paginate")
    def test_get_commits_passes_api_key(self, mock_paginate):
        mock_paginate.return_value = []

        github.get_commits("owner", "repo", api_key="secret")

        mock_paginate.assert_called_once_with(
            "owner", "repo", "/commits", api_key="secret"
        )

    @patch("provider._paginate")
    def test_get_commits_raises_type_error_if_not_list(self, mock_paginate):
        mock_paginate.side_effect = TypeError("Expected list response from API, got dict")

        with self.assertRaises(TypeError):
            github.get_commits("owner", "repo")

    @patch("provider._paginate")
    def test_empty_repo_409_returns_empty_list(self, mock_paginate):
        error = requests.exceptions.HTTPError("409")
        error.response = MagicMock(status_code=409)
        mock_paginate.side_effect = error

        result, truncated = github.get_commits("owner", "repo")

        self.assertEqual(result, [])
        self.assertFalse(truncated)

    @patch("provider._paginate")
    def test_other_http_errors_are_reraised(self, mock_paginate):
        error = requests.exceptions.HTTPError("404")
        error.response = MagicMock(status_code=404)
        mock_paginate.side_effect = error

        with self.assertRaises(requests.exceptions.HTTPError):
            github.get_commits("owner", "repo")


class TestGetContributors(unittest.TestCase):
    @patch("provider._paginate")
    def test_get_contributors_returns_tuple(self, mock_paginate):
        contributors = [{"login": "Alice", "contributions": 5}]
        mock_paginate.return_value = (contributors, False)

        result, truncated = github.get_contributors("owner", "repo")

        self.assertIsInstance(result, list)
        self.assertFalse(truncated)
        self.assertEqual(result[0]["login"], "Alice")
        mock_paginate.assert_called_once_with(
            "owner", "repo", "/contributors", api_key=None
        )

    @patch("provider._paginate")
    def test_get_contributors_passes_api_key(self, mock_paginate):
        mock_paginate.return_value = []

        github.get_contributors("owner", "repo", api_key="secret")

        mock_paginate.assert_called_once_with(
            "owner", "repo", "/contributors", api_key="secret"
        )

    @patch("provider._paginate")
    def test_get_contributors_raises_type_error_if_not_list(self, mock_paginate):
        mock_paginate.side_effect = TypeError("Expected list response from API, got dict")

        with self.assertRaises(TypeError):
            github.get_contributors("owner", "repo")


class TestGetLanguages(unittest.TestCase):
    @patch("provider._fetch")
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

    @patch("provider._fetch")
    def test_get_languages_passes_api_key(self, mock_fetch):
        mock_fetch.return_value = _mock_response({"Python": 10})

        github.get_languages("owner", "repo", api_key="secret")

        mock_fetch.assert_called_once_with(
            "https://api.github.com/repos/owner/repo/languages",
            api_key="secret",
            expected_type=dict,
        )

    @patch("provider.requests.get")
    def test_get_languages_raises_type_error_if_not_dict(self, mock_get):
        mock_get.return_value = _mock_response([])

        with self.assertRaises(TypeError):
            github.get_languages("owner", "repo")


class TestGetIssues(unittest.TestCase):
    @patch("provider._paginate")
    def test_get_issues_returns_tuple(self, mock_paginate):
        issues = [
            {"number": 1, "state": "open"},
            {"number": 2, "state": "closed"},
        ]
        mock_paginate.return_value = (issues, False)

        result, truncated = github.get_issues("owner", "repo")

        self.assertIsInstance(result, list)
        self.assertFalse(truncated)
        self.assertEqual(len(result), 2)
        mock_paginate.assert_called_once_with(
            "owner", "repo", "/issues?state=all", api_key=None
        )

    @patch("provider._paginate")
    def test_get_issues_passes_api_key(self, mock_paginate):
        mock_paginate.return_value = []

        github.get_issues("owner", "repo", api_key="secret")

        mock_paginate.assert_called_once_with(
            "owner", "repo", "/issues?state=all", api_key="secret"
        )

    @patch("provider._paginate")
    def test_get_issues_raises_type_error_if_not_list(self, mock_paginate):
        mock_paginate.side_effect = TypeError("Expected list response from API, got dict")

        with self.assertRaises(TypeError):
            github.get_issues("owner", "repo")


if __name__ == "__main__":
    unittest.main()
