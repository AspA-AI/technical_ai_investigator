"""
Colored logging for the investigation copilot backend.

Usage in any module:

    from utils.logger import get_logger

    log = get_logger(__name__)
    log.info("Server started")
    log.warning("Deprecated path")
    log.error("Upload failed", exc_info=True)

    # Optional category tag (extra color on the label):
    log.api("POST /api/upload")
    log.service("Ingestion finished")
    log.agent("LangGraph node: anomaly_detector")
    log.tool("AnomalyDetector.run")
    log.db("Inserted 1200 sensor rows")
"""

from __future__ import annotations

import logging
import os
import sys
from enum import Enum
from typing import Any

_CONFIGURED = False


class LogCategory(str, Enum):
    """Semantic log categories (shown as a colored tag in the console)."""

    APP = "APP"
    API = "API"
    PIPELINE = "PIPELINE"
    SERVICE = "SERVICE"
    AGENT = "AGENT"
    TOOL = "TOOL"
    DB = "DB"
    HTTP = "HTTP"


# ANSI colors
_RESET = "\033[0m"
_DIM = "\033[2m"
_BOLD = "\033[1m"

_LEVEL_COLORS = {
    logging.DEBUG: "\033[36m",  # cyan
    logging.INFO: "\033[32m",  # green
    logging.WARNING: "\033[33m",  # yellow
    logging.ERROR: "\033[31m",  # red
    logging.CRITICAL: "\033[35m\033[1m",  # bold magenta
}

_CATEGORY_COLORS = {
    LogCategory.APP: "\033[37m",  # white
    LogCategory.API: "\033[94m",  # bright blue
    LogCategory.PIPELINE: "\033[97m\033[1m",  # bold white
    LogCategory.SERVICE: "\033[92m",  # bright green
    LogCategory.AGENT: "\033[95m",  # bright magenta
    LogCategory.TOOL: "\033[96m",  # bright cyan
    LogCategory.DB: "\033[93m",  # bright yellow
    LogCategory.HTTP: "\033[90m",  # gray
}


def _supports_color() -> bool:
    if os.getenv("NO_COLOR"):
        return False
    if os.getenv("FORCE_COLOR") or os.getenv("LOG_COLOR", "").lower() in ("1", "true", "yes"):
        return True
    return hasattr(sys.stderr, "isatty") and sys.stderr.isatty()


def _colorize(text: str, color: str, *, enabled: bool) -> str:
    if not enabled or not color:
        return text
    return f"{color}{text}{_RESET}"


class ColoredFormatter(logging.Formatter):
    """Console formatter with level and optional category colors."""

    def __init__(self, *, use_color: bool = True) -> None:
        super().__init__(datefmt="%Y-%m-%d %H:%M:%S")
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        use_color = self.use_color
        level_color = _LEVEL_COLORS.get(record.levelno, "")
        level_name = _colorize(f"{record.levelname:8}", level_color, enabled=use_color)

        category = getattr(record, "log_category", None)
        if category:
            cat_key = (
                category
                if isinstance(category, LogCategory)
                else LogCategory(str(category))
            )
            cat_color = _CATEGORY_COLORS.get(cat_key, _DIM)
            category_part = _colorize(f"{cat_key.value:8}", cat_color, enabled=use_color)
        else:
            category_part = _colorize(f"{'':8}", _DIM, enabled=use_color)

        timestamp = _colorize(
            self.formatTime(record, self.datefmt),
            _DIM,
            enabled=use_color,
        )
        logger_name = _colorize(record.name, _DIM, enabled=use_color)
        message = record.getMessage()

        if record.exc_info and not record.exc_text:
            record.exc_text = self.formatException(record.exc_info)

        line = f"{timestamp} | {level_name} | {category_part} | {logger_name} | {message}"
        if record.exc_text:
            exc = record.exc_text
            if use_color:
                exc = _colorize(exc, _LEVEL_COLORS[logging.ERROR], enabled=True)
            line = f"{line}\n{exc}"
        return line


class AppLogger:
    """
    Thin wrapper around stdlib logging with category helpers.

    Supports: debug, info, warning, error, critical, exception,
    and api / service / agent / tool / db / http for typed messages.
    """

    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(name)

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.debug(msg, *args, **kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.info(msg, *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.error(msg, *args, **kwargs)

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.critical(msg, *args, **kwargs)

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("exc_info", True)
        self._logger.error(msg, *args, **kwargs)

    def log(
        self,
        level: int,
        msg: str,
        *args: Any,
        category: LogCategory | str | None = None,
        **kwargs: Any,
    ) -> None:
        extra = kwargs.setdefault("extra", {})
        if category is not None:
            extra["log_category"] = category
        self._logger.log(level, msg, *args, **kwargs)

    def api(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.log(logging.INFO, msg, *args, category=LogCategory.API, **kwargs)

    def service(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.log(logging.INFO, msg, *args, category=LogCategory.SERVICE, **kwargs)

    def agent(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.log(logging.INFO, msg, *args, category=LogCategory.AGENT, **kwargs)

    def tool(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.log(logging.INFO, msg, *args, category=LogCategory.TOOL, **kwargs)

    def db(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.log(logging.INFO, msg, *args, category=LogCategory.DB, **kwargs)

    def http(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.log(logging.INFO, msg, *args, category=LogCategory.HTTP, **kwargs)

    def pipeline(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self.log(logging.INFO, msg, *args, category=LogCategory.PIPELINE, **kwargs)


def setup_logging(
    *,
    level: int | str | None = None,
    debug: bool | None = None,
    use_color: bool | None = None,
) -> None:
    """
    Configure root logging once (call from app.py on startup).

    Args:
        level: logging level name or int (default: DEBUG if debug else INFO)
        debug: shorthand to set level to DEBUG when True
        use_color: force ANSI colors on/off (default: auto-detect TTY)
    """
    global _CONFIGURED

    if debug is True:
        resolved_level = logging.DEBUG
    elif level is not None:
        resolved_level = (
            logging.getLevelName(level.upper())
            if isinstance(level, str)
            else level
        )
    else:
        resolved_level = logging.INFO

    color_enabled = _supports_color() if use_color is None else use_color
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(ColoredFormatter(use_color=color_enabled))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(resolved_level)

    # Quieter third-party loggers unless debugging
    if resolved_level > logging.DEBUG:
        for name in ("urllib3", "httpx", "httpcore", "openai", "sqlalchemy.engine"):
            logging.getLogger(name).setLevel(logging.WARNING)

    # Align uvicorn with our formatter when running under uvicorn
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(name)
        uv_logger.handlers.clear()
        uv_logger.propagate = True

    _CONFIGURED = True
    get_logger("utils.logger").info(
        "Logging configured (level=%s, color=%s)",
        logging.getLevelName(resolved_level),
        color_enabled,
        extra={"log_category": LogCategory.APP},
    )


def get_logger(name: str | None = None) -> AppLogger:
    """
    Return a logger for the calling module.

    Example:
        log = get_logger(__name__)
    """
    if not _CONFIGURED:
        try:
            from config.settings import settings

            setup_logging(debug=settings.DEBUG)
        except Exception:
            setup_logging(debug=True)
    logger_name = name if name else "app"
    return AppLogger(logger_name)
