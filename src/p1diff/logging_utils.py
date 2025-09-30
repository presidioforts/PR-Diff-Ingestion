"""Logging configuration utilities for P1 Diff."""

import logging
import os
from typing import Optional

_LOG_FORMAT = (
    "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)


def configure_logging(level: Optional[str] = None) -> None:
    """Configure application-wide logging once."""
    if logging.getLogger().handlers:
        return

    log_level = level or os.getenv("LOG_LEVEL", "INFO")
    logging.basicConfig(level=log_level.upper(), format=_LOG_FORMAT)
