import json
import logging
import sys
from datetime import UTC, datetime

_RESERVED = frozenset(
    {
        "args", "msg", "levelname", "levelno", "pathname", "filename", "module",
        "exc_info", "exc_text", "stack_info", "lineno", "funcName", "created",
        "msecs", "relativeCreated", "thread", "threadName", "processName",
        "process", "name", "message", "taskName",
    }
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.now(UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        for key, value in record.__dict__.items():
            if key in _RESERVED or key.startswith("_"):
                continue
            payload[key] = value
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    for existing in list(root.handlers):
        root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(level.upper())
    # aiogram is chatty at INFO; tone it down a touch.
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)
    # CRITICAL: aiohttp's request logger emits the full URL at DEBUG, and
    # Telegram bot API URLs contain the bot token (api.telegram.org/bot<TOKEN>/…).
    # Pin these loggers at INFO regardless of root level so the token can't
    # leak into journald even if someone runs LOG_LEVEL=DEBUG in prod.
    for noisy in ("aiohttp.client", "aiohttp.access", "aiohttp.internal"):
        logging.getLogger(noisy).setLevel(logging.INFO)
