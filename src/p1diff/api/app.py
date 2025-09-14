"""FastAPI application for P1 Diff MCP API."""

import subprocess
import sys
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import __version__
from .models import DiffRequest, HealthResponse, VersionResponse
from .service import DiffService


# Create FastAPI app
app = FastAPI(
    title="P1 Diff API",
    description="Deterministic Git diff ingestion API for MCP integration",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware for MCP integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize service
diff_service = DiffService()


def get_git_version() -> str:
    """Get git version if available."""
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip().split()[-1]
    except Exception:
        pass
    return None


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler to ensure consistent error responses."""
    return JSONResponse(
        status_code=500,
        content={
            "ok": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": f"Internal server error: {str(exc)}",
                "details": {
                    "exception_type": type(exc).__name__,
                    "path": str(request.url.path)
                }
            }
        }
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    git_version = get_git_version()
    return HealthResponse(
        status="healthy",
        version=__version__,
        git_available=git_version is not None,
        git_version=git_version
    )


@app.get("/version", response_model=VersionResponse)
async def version_info():
    """Version information endpoint."""
    git_version = get_git_version()
    return VersionResponse(
        version=__version__,
        api_version="v1",
        git_version=git_version
    )


@app.post("/diff")
async def create_diff(request: DiffRequest) -> Dict[str, Any]:
    """
    Create a deterministic diff between two commits.
    
    This endpoint returns the exact same JSON structure as the CLI tool,
    suitable for consumption by AI agents and LLMs for code analysis.
    
    The response contains complete diff information including:
    - File-by-file changes with detailed hunks
    - Line-by-line patch content
    - Metadata and provenance information
    - Capacity management and truncation details
    """
    try:
        # Process the diff request using the service layer
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
        
        # Return the result directly - it's already in the correct format
        return result
        
    except Exception as e:
        # This should be caught by the service layer, but just in case
        raise HTTPException(
            status_code=500,
            detail={
                "ok": False,
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": f"Failed to process diff: {str(e)}",
                    "details": {"exception_type": type(e).__name__}
                }
            }
        )


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "P1 Diff API",
        "version": __version__,
        "description": "Deterministic Git diff ingestion API for MCP integration",
        "endpoints": {
            "diff": "POST /diff - Create deterministic diff",
            "health": "GET /health - Health check",
            "version": "GET /version - Version information",
            "docs": "GET /docs - API documentation"
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
