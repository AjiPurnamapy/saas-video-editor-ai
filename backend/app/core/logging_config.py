"""
Logging configuration module.

Sets up structured JSON logging for the application.
All modules should use `logging.getLogger(__name__)` to get a logger.

Improvements over basic logging:
- Structured JSON with ISO-8601 timestamps for log aggregation
- Process/thread identifiers for debugging concurrent issues
- Separate formatters for dev (readable) and prod (JSON)
- Configurable per-module log levels
"""

import logging
import logging.config


def setup_logging(level: str = "INFO", json_format: bool = True) -> None:
    """Configure the application logging system.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_format: If True, use structured JSON format suitable for
                     log aggregation tools (ELK, CloudWatch, Datadog).
                     If False, use human-readable plain text for local dev.
    """
    if json_format:
        fmt = (
            '{"time":"%(asctime)s",'
            '"level":"%(levelname)s",'
            '"logger":"%(name)s",'
            '"module":"%(module)s",'
            '"function":"%(funcName)s",'
            '"line":%(lineno)d,'
            '"process":%(process)d,'
            '"thread":%(thread)d,'
            '"message":"%(message)s"}'
        )
    else:
        fmt = (
            "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | "
            "%(message)s"
        )

    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": fmt,
                "datefmt": "%Y-%m-%dT%H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
        },
        "root": {
            "level": level.upper(),
            "handlers": ["console"],
        },
        "loggers": {
            # Application loggers
            "app": {
                "level": level.upper(),
                "handlers": ["console"],
                "propagate": False,
            },
            # Reduce noise from third-party libraries
            "uvicorn": {"level": "INFO"},
            "uvicorn.access": {"level": "WARNING"},
            "sqlalchemy.engine": {"level": "WARNING"},
            "passlib": {"level": "WARNING"},
        },
    }

    logging.config.dictConfig(config)
