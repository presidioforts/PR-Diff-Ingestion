"""Diff routes for P1 Diff API."""

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from ..models import DiffRequest
from ..services import DiffService

router = APIRouter(tags=["diff"])

logger = logging.getLogger(__name__)

diff_service = DiffService()


@router.post("/diff")
def create_diff(request: DiffRequest) -> Dict[str, Any]:
    """Create a deterministic diff between two commits."""
    logger.info(
        "Received diff request",
        extra={
            "repo": request.repo_url,
            "good": request.commit_good,
            "candidate": request.commit_candidate,
        },
    )

    try:
        result = diff_service.process_diff_request(
            repo_url=request.repo_url,
            commit_good=request.commit_good,
            commit_candidate=request.commit_candidate,
            branch_name=request.branch_name,
            cap_total=request.cap_total,
            cap_file=request.cap_file,
            context_lines=request.context_lines,
            find_renames_threshold=request.find_renames_threshold,
        )
        logger.info(
            "Diff request completed",
            extra={
                "repo": request.repo_url,
                "files": len(result.get("data", {}).get("files", [])),
            },
        )
        return result

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Diff request failed", extra={"repo": request.repo_url})
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Failed to process diff: {str(exc)}",
                    "details": {"exception_type": type(exc).__name__},
                },
            },
        ) from exc
