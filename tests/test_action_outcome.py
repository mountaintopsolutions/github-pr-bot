"""The GitHub Action must not report success for a tool that hard-failed."""

import asyncio

import pytest

from pr_agent.config_loader import get_settings
from pr_agent.servers.github_action_runner import (ToolFailure, report_outcome,
                                                   run_tool)


class _Tool:
    """Stand-in for PRDescription / PRReviewer / PRCodeSuggestions."""

    def __init__(self, run_failed=False, raises=None):
        self.run_failed = run_failed
        self._raises = raises

    async def run(self):
        if self._raises:
            raise self._raises


def _run(coro):
    return asyncio.run(coro)


def test_tool_that_swallowed_an_error_is_not_reported_as_completed():
    assert _run(run_tool("PR review", lambda: _Tool(run_failed=True))) is False


def test_tool_that_raises_is_reported_as_failed():
    assert _run(run_tool("PR review", lambda: _Tool(raises=RuntimeError("boom")))) is False


def test_failure_constructing_a_tool_is_reported_as_failed():
    def factory():
        raise RuntimeError("no such PR")

    assert _run(run_tool("PR review", factory)) is False


def test_successful_tool_is_reported_as_completed():
    assert _run(run_tool("PR review", lambda: _Tool())) is True


@pytest.mark.parametrize("policy,results,should_fail", [
    # default: only a total failure fails the step
    ("all", {"describe": False, "review": False, "improve": False}, True),
    ("all", {"describe": True, "review": False, "improve": False}, False),
    ("all", {"describe": True, "review": True}, False),
    ("any", {"describe": True, "review": False}, True),
    ("any", {"describe": True, "review": True}, False),
    ("none", {"describe": False, "review": False}, False),
    # boolean-ish values from action inputs
    ("true", {"describe": True, "review": False}, True),
    ("false", {"describe": False, "review": False}, False),
    # unknown values fall back to the default policy
    ("banana", {"describe": False, "review": False}, True),
])
def test_exit_policy(policy, results, should_fail):
    get_settings().set("CONFIG.FAIL_ON_TOOL_ERROR", policy)
    if should_fail:
        with pytest.raises(ToolFailure):
            report_outcome(results)
    else:
        report_outcome(results)


def test_no_enabled_tools_never_fails():
    get_settings().set("CONFIG.FAIL_ON_TOOL_ERROR", "any")
    report_outcome({})


EVENT = {
    "action": "opened",
    "pull_request": {"url": "https://api.github.com/repos/o/r/pulls/1", "draft": False, "body": ""},
}


def _enable_all_tools(monkeypatch, **tools):
    import pr_agent.servers.github_action_runner as runner

    get_settings().set("GITHUB_ACTION_CONFIG.AUTO_DESCRIBE", True)
    get_settings().set("GITHUB_ACTION_CONFIG.AUTO_REVIEW", True)
    get_settings().set("GITHUB_ACTION_CONFIG.AUTO_IMPROVE", True)
    get_settings().set("CONFIG.ENABLE_AUTO_APPROVAL", False)
    for name, failed in tools.items():
        monkeypatch.setattr(runner, name, lambda *a, _f=failed, **kw: _Tool(run_failed=_f))
    return runner


def test_every_tool_failing_fails_the_run(monkeypatch):
    runner = _enable_all_tools(monkeypatch, PRDescription=True, PRReviewer=True,
                               PRCodeSuggestions=True)
    get_settings().set("CONFIG.FAIL_ON_TOOL_ERROR", "all")
    with pytest.raises(ToolFailure):
        _run(runner.handle_pull_request_event(EVENT))


def test_one_tool_failing_does_not_fail_the_run_by_default(monkeypatch):
    runner = _enable_all_tools(monkeypatch, PRDescription=False, PRReviewer=False,
                               PRCodeSuggestions=True)
    get_settings().set("CONFIG.FAIL_ON_TOOL_ERROR", "all")
    _run(runner.handle_pull_request_event(EVENT))  # the other two still ran and published


def test_one_tool_failing_fails_the_run_under_the_any_policy(monkeypatch):
    runner = _enable_all_tools(monkeypatch, PRDescription=False, PRReviewer=False,
                               PRCodeSuggestions=True)
    get_settings().set("CONFIG.FAIL_ON_TOOL_ERROR", "any")
    with pytest.raises(ToolFailure):
        _run(runner.handle_pull_request_event(EVENT))
