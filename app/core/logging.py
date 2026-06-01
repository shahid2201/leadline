import logging
from typing import Any

from pythonjsonlogger.json import JsonFormatter


class RequestContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        defaults: dict[str, Any] = {
            "request_id": None,
            "tenant_id": None,
            "user_id": None,
            "path": None,
            "method": None,
            "status_code": None,
            "latency_ms": None,
        }
        for key, value in defaults.items():
            if not hasattr(record, key):
                setattr(record, key, value)
        return True


def configure_logging(level: str) -> None:
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level.upper())

    handler = logging.StreamHandler()
    formatter = JsonFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s "
        "%(request_id)s %(tenant_id)s %(user_id)s %(path)s %(method)s "
        "%(status_code)s %(latency_ms)s"
    )
    handler.setFormatter(formatter)
    handler.addFilter(RequestContextFilter())

    root_logger.addHandler(handler)
