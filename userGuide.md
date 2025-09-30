# P1 Diff API User Guide

## Overview
P1 Diff ingests deterministic Git diffs and produces stable JSON for MCP/LLM workflows. You can run it as a CLI or via the FastAPI service; this guide focuses on the API experience.

## Quick Start
1. Install dependencies and prepare a virtual environment (Python 3.11+).
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # optional, for testing
   ```
2. Provide Git credentials and logging level:
   ```env
   GIT_USERNAME=your-username
   GIT_AUTH_TOKEN=ghp_xxx
   LOG_LEVEL=INFO
   ```
   Define these in `.env` or export them before launching the server.
3. Start the API from the project root:
   ```bash
   uvicorn p1diff.api.app:app --host 0.0.0.0 --port 8000
   ```

## API Endpoints
- `POST /diff` — Generate a diff payload (requires repo details in the request body).
- `GET /health` — Check service health and git availability.
- `GET /version` — View API version metadata.
- `GET /docs` — Swagger UI for exploration.

### Sample Diff Request
```http
POST http://127.0.0.1:8000/diff
Content-Type: application/json

{
  "repo_url": "https://github.com/your-org/your-repo.git",
  "commit_good": "abc123",
  "commit_candidate": "def456",
  "branch_name": "feature/my-feature",
  "cap_total": 800000,
  "cap_file": 64000,
  "context_lines": 3,
  "find_renames_threshold": 90
}
```

### Response Structure
- `ok`: Boolean success flag.
- `data.provenance`: Run metadata (repo, commits, git version, checksum).
- `data.files`: Per-file diff details (hunks, flags, sizes, submodule info).
- `data.notes`: Summary messages (omitted files, whitespace-only changes, etc.).

## Logging
- Logging defaults to `INFO`. Adjust by setting the `LOG_LEVEL` environment variable (e.g., `DEBUG`, `WARNING`).
- Core modules emit detailed progress: repository cloning/fetch, file processing, capacity enforcement, serialization, and diff routing.

## Testing
Run the full test suite to validate functionality:
```bash
python -m pytest
```

## Deployment Tips
- Ensure `git` is available in your runtime image/container.
- Provide `GIT_USERNAME`/`GIT_AUTH_TOKEN` for private repositories.
- Tail service logs to monitor ingestion stages and quickly diagnose failures.
