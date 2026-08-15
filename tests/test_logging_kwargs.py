"""Structured log kwargs must never break the logging call itself.

loguru interpolates the message with `message.format(**kwargs)` as soon as any kwargs are passed.
Messages here are built with f-strings and routinely contain interpolated API error bodies such as
`{"message": "Not Found"}`, which used to raise `KeyError: '"message"'` from inside the logging
call and abort the caller.
"""

import sys

from pr_agent.log import LoggingFormat, get_logger, setup_logger


def _capture(func):
    records = []
    logger = get_logger()
    handler_id = logger.add(lambda msg: records.append(msg.record), level="DEBUG")
    try:
        func()
    finally:
        logger.remove(handler_id)
    return records


def test_message_with_json_braces_and_kwargs_does_not_raise():
    message = 'Error getting main issue: 404 {"message": "Not Found"}'
    records = _capture(lambda: get_logger().error(message, artifact={"traceback": "..."}))
    assert len(records) == 1
    assert records[0]["message"] == message  # left uninterpolated
    assert records[0]["extra"]["artifact"] == {"traceback": "..."}


def test_kwargs_are_still_recorded_as_extra():
    records = _capture(lambda: get_logger().info("statistics", analytics=True, count=3))
    assert records[0]["extra"] == {"analytics": True, "count": 3}


def test_log_call_site_is_reported_not_the_wrapper():
    records = _capture(lambda: get_logger().warning("hello", artifact={}))
    assert records[0]["file"].name == "test_logging_kwargs.py"


def test_contextualize_and_other_loguru_attributes_still_work():
    logger = get_logger()
    with logger.contextualize(sub_feature="x"):
        records = _capture(lambda: get_logger().debug("in context"))
    assert records[0]["extra"]["sub_feature"] == "x"


def test_error_handler_logging_a_json_api_body_does_not_re_raise(monkeypatch):
    """Regression: `KeyError: '"message"'` escaping an except block that logs a GitHub error body.

    The handler logs `f"...{e}"` with an `artifact=` kwarg; when the exception text carries a JSON
    body the logging call itself used to raise, so the caller aborted instead of continuing.
    """
    from pr_agent.tools import ticket_pr_compliance_check as ticket_check

    class _Exploding:
        def findall(self, text):
            raise Exception('404 {"message": "Not Found", "status": "404"}')

    monkeypatch.setattr(ticket_check, "GITHUB_TICKET_PATTERN", _Exploding())
    assert ticket_check.extract_ticket_links_from_pr_description("body #12", "org/repo") == []


def test_setup_logger_returns_a_usable_logger():
    logger = setup_logger(level="DEBUG", fmt=LoggingFormat.CONSOLE)
    logger.info('setup {"message": "ok"}', artifact={"a": 1})
