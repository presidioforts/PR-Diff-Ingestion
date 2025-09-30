"""FastAPI application instance for the P1 Diff API."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from ..logging_utils import configure_logging
from . import __version__
from .routes import router as api_router

configure_logging()

app = FastAPI(
    title="P1 Diff API",
    description="Deterministic Git diff ingestion API for MCP integration",
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Return a consistent error envelope for uncaught exceptions."""
    return JSONResponse(
        status_code=500,
        content={
            "ok": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": f"Internal server error: {str(exc)}",
                "details": {
                    "exception_type": type(exc).__name__,
                    "path": str(request.url.path),
                },
            },
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
