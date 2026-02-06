from __future__ import annotations

import json
import logging
import sys
from typing import Any


def _json_formatter(record: logging.LogRecord) -> str:
    payload: dict[str, Any] = {
        "level": record.levelname.lower(),
        "name": record.name,
        "message": record.getMessage(),
    }
    if record.exc_info:
        payload["exc_info"] = logging.Formatter().formatException(record.exc_info)
    return json.dumps(payload)


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return _json_formatter(record)


def setup_logging(level: str = "INFO") -> None:
    numeric_level = logging.getLevelName(level.upper())
    if isinstance(numeric_level, str):
        numeric_level = logging.INFO

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonLogFormatter())

    root = logging.getLogger()
    root.setLevel(numeric_level)
    root.handlers = [handler]
