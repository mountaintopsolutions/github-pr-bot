import os
os.environ["AUTO_CAST_FOR_DYNACONF"] = "false"
import json
import logging
import sys
from enum import Enum

from loguru import logger

from pr_agent.config_loader import get_settings


class LoggingFormat(str, Enum):
    CONSOLE = "CONSOLE"
    JSON = "JSON"


def json_format(record: dict) -> str:
    return record["message"]


def analytics_filter(record: dict) -> bool:
    return record.get("extra", {}).get("analytics", False)


def inv_analytics_filter(record: dict) -> bool:
    return not record.get("extra", {}).get("analytics", False)


def setup_logger(level: str = "INFO", fmt: LoggingFormat = LoggingFormat.CONSOLE):
    level: int = logging.getLevelName(level.upper())
    if type(level) is not int:
        level = logging.INFO

    if fmt == LoggingFormat.JSON and os.getenv("LOG_SANE", "0").lower() == "0":  # better debugging github_app
        logger.remove(None)
        logger.add(
            sys.stdout,
            filter=inv_analytics_filter,
            level=level,
            format="{message}",
            colorize=False,
            serialize=True,
        )
    elif fmt == LoggingFormat.CONSOLE: # does not print the 'extra' fields
        logger.remove(None)
        logger.add(sys.stdout, level=level, colorize=True, filter=inv_analytics_filter)

    log_folder = get_settings().get("CONFIG.ANALYTICS_FOLDER", "")
    if log_folder:
        pid = os.getpid()
        log_file = os.path.join(log_folder, f"github-pr-bot.{pid}.log")
        logger.add(
            log_file,
            filter=analytics_filter,
            level=level,
            format="{message}",
            colorize=False,
            serialize=True,
        )

    return get_logger()


_LOG_METHODS = ("trace", "debug", "info", "success", "warning", "error", "critical", "exception")


class _StructuredLogger:
    """Thin proxy around loguru's logger that treats keyword arguments as structured
    context ('extra') rather than as str.format() arguments.

    loguru interpolates the message with ``message.format(*args, **kwargs)`` as soon as any
    args or kwargs are passed. This codebase builds messages with f-strings and passes
    structured payloads as kwargs (``artifact=...``, ``description=...``), so a message that
    happens to contain braces - e.g. a GitHub API error body ``{"message": "Not Found"}``
    interpolated into the message - made the logging call itself raise
    ``KeyError: '"message"'``, aborting the caller instead of logging.

    Keyword arguments are therefore bound as extras (same place loguru would have put them,
    so JSON output is unchanged) and the message is left uninterpolated.
    """

    def __getattr__(self, name):
        return getattr(logger, name)

    def __repr__(self):
        return f"<StructuredLogger {logger!r}>"

    @staticmethod
    def _emit(level_method, message, args, kwargs, depth=1):
        bound = logger.bind(**kwargs) if kwargs else logger
        try:
            return getattr(bound.opt(depth=depth), level_method)(message, *args)
        except (KeyError, IndexError, ValueError):
            # positional args could not be interpolated into the message (unbalanced/rogue
            # braces). Log the raw message rather than losing the record entirely.
            return getattr(bound.opt(depth=depth), level_method)(message)

    def log(self, level, message, *args, **kwargs):
        bound = logger.bind(**kwargs) if kwargs else logger
        try:
            return bound.opt(depth=1).log(level, message, *args)
        except (KeyError, IndexError, ValueError):
            return bound.opt(depth=1).log(level, message)


def _add_log_method(name):
    def method(self, message, *args, **kwargs):
        return _StructuredLogger._emit(name, message, args, kwargs, depth=2)

    method.__name__ = name
    setattr(_StructuredLogger, name, method)


for _name in _LOG_METHODS:
    _add_log_method(_name)

_structured_logger = _StructuredLogger()


def get_logger(*args, **kwargs):
    return _structured_logger
