"""Meta endpoints for P1 Diff API."""

import logging
import subprocess
from typing import Optional

from fastapi import APIRouter

from .. import __version__
from ..models import HealthResponse, VersionResponse

router = APIRouter(tags=["meta"])

logger = logging.getLogger(__name__)


def _get_git_version() -> Optional[str]:
    """Return the installed git version if available."""
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip().split()[-1]
    except Exception as exc:
        logger.debug("git --version check failed", exc_info=exc)
    return None


@router.get("/health", response_model=HealthResponse)
def health_check() -> HealthResponse:
    """Health check endpoint."""
    git_version = _get_git_version()
    logger.info(
        "Health check invoked",
        extra={"git_available": git_version is not None, "git_version": git_version},
    )
    return HealthResponse(
        status="healthy",
        version=__version__,
        git_available=git_version is not None,
        git_version=git_version,
    )


@router.get("/version", response_model=VersionResponse)
def version_info() -> VersionResponse:
    """Version information endpoint."""
    git_version = _get_git_version()
    logger.info("Version endpoint invoked", extra={"git_version": git_version})
    return VersionResponse(
        version=__version__,
        api_version="v1",
        git_version=git_version,
    )


@router.get("/", include_in_schema=False)
def root() -> dict:
    """Root endpoint providing basic API metadata."""
    logger.debug("Root endpoint served")
    return {
        "name": "P1 Diff API",
        "version": __version__,
        "description": "Deterministic Git diff ingestion API for MCP integration",
        "endpoints": {
            "diff": "POST /diff - Create deterministic diff",
            "health": "GET /health - Health check",
            "version": "GET /version - Version information",
            "docs": "GET /docs - API documentation",
        },
    }
