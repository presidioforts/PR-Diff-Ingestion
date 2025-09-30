"""API route registration for P1 Diff."""

from fastapi import APIRouter

from . import diff, meta

router = APIRouter()
router.include_router(meta.router)
router.include_router(diff.router)

__all__ = ["router"]
