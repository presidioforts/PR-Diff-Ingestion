"""Application-wide settings and environment loading."""

import logging
import os
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()
logger.debug("Environment variables loaded from .env if present")


@lru_cache(maxsize=1)
def get_git_credentials() -> tuple[Optional[str], Optional[str]]:
    """Return Git credentials from environment variables."""
    username = os.getenv("GIT_USERNAME")
    token = os.getenv("GIT_AUTH_TOKEN")
    if username and token:
        logger.debug("Git credentials retrieved", extra={"username": username})
        return username, token

    logger.debug("Git credentials not configured")
    return None, None
