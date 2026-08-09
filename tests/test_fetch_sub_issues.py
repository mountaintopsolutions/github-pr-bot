"""A GraphQL response for a missing issue must not blow up sub-issue lookup."""

import json

from pr_agent.git_providers.github_provider import GithubProvider

NOT_FOUND_RESPONSE = {
    "data": {"repository": {"issue": None}},
    "errors": [{"type": "NOT_FOUND", "path": ["repository", "issue"]}],
}


class _Requester:
    def __init__(self, payload):
        self.payload = payload

    def requestJson(self, method, path, input=None):
        return (200, {}, json.dumps(self.payload))


class _Client:
    def __init__(self, payload):
        setattr(self, "_Github__requester", _Requester(payload))


class _Provider:
    """Enough of GithubProvider to drive fetch_sub_issues without any network."""

    fetch_sub_issues = GithubProvider.fetch_sub_issues

    def __init__(self, payload):
        self.github_client = _Client(payload)


def test_missing_issue_returns_no_sub_issues_instead_of_raising():
    # `.get("issue", {})` returns None here, because the key is present with a null value, so
    # chaining `.get("id")` onto it used to raise AttributeError
    provider = _Provider(NOT_FOUND_RESPONSE)
    assert provider.fetch_sub_issues("https://github.com/o/r/issues/1") == set()


def test_null_data_returns_no_sub_issues():
    provider = _Provider({"data": None, "errors": [{"type": "FORBIDDEN"}]})
    assert provider.fetch_sub_issues("https://github.com/o/r/issues/1") == set()


def test_null_repository_returns_no_sub_issues():
    provider = _Provider({"data": {"repository": None}})
    assert provider.fetch_sub_issues("https://github.com/o/r/issues/1") == set()
