# P1 Diff API Usage Guide

A comprehensive guide for using the P1 Diff MCP API for deterministic Git diff analysis.

## Overview

The P1 Diff API provides a REST interface for generating deterministic, capped, per-file unified diffs between Git commits. It's designed specifically for MCP (Model Context Protocol) integration, allowing AI agents to analyze code changes with complete diff information.

## Quick Start

### 1. Start the API Server

```bash
# Development mode (with auto-reload)
python scripts/start_api.py --host 127.0.0.1 --port 8000 --reload

# Production mode
python scripts/start_api.py --host 0.0.0.0 --port 8000 --workers 4

# Using Makefile
make api-dev    # Development
make api-start  # Production
```

### 2. Verify Server is Running

```bash
# Health check
curl http://127.0.0.1:8000/health

# Or using PowerShell
Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -Method GET
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "git_available": true,
  "git_version": "2.50.0"
}
```

## API Endpoints

### 1. POST /diff - Generate Diff Analysis

**Purpose**: Generate deterministic diff between two commits with complete analysis data for LLM consumption.

**URL**: `POST http://127.0.0.1:8000/diff`

**Content-Type**: `application/json`

#### Request Body

```json
{
  "repo_url": "https://github.com/user/repo.git",
  "commit_good": "ba7765dd48c0ba51f4fd12cde48fd100aecdb743",
  "commit_candidate": "d7a39abec5a282b9955afdd1649a5f1bafae35f7",
  "branch_name": "feature/new-feature",
  "cap_total": 800000,
  "cap_file": 64000,
  "context_lines": 3,
  "find_renames_threshold": 90
}
```

#### Request Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `repo_url` | string | ✅ | - | Repository URL (https/http) or local path |
| `commit_good` | string | ✅ | - | Good commit SHA (baseline) |
| `commit_candidate` | string | ✅ | - | Candidate commit SHA (comparison target) |
| `branch_name` | string | ❌ | null | Branch name for context and fetch hint |
| `cap_total` | integer | ❌ | 800000 | Total capacity limit in bytes (1000-10000000) |
| `cap_file` | integer | ❌ | 64000 | Per-file capacity limit in bytes (100-1000000) |
| `context_lines` | integer | ❌ | 3 | Number of context lines in diffs (0-10) |
| `find_renames_threshold` | integer | ❌ | 90 | Rename detection threshold percentage (0-100) |

#### Response Format

**Success Response (200 OK)**:
```json
{
  "ok": true,
  "data": {
    "provenance": {
      "repo_url": "https://github.com/user/repo.git",
      "commit_good": "ba7765dd...",
      "commit_candidate": "d7a39abe...",
      "branch_name": "feature/new-feature",
      "caps": {
        "total_bytes": 800000,
        "per_file_bytes": 64000,
        "context_lines": 3
      },
      "rename_detection": {
        "enabled": true,
        "threshold_pct": 90
      },
      "git_version": "2.50.0",
      "diff_algorithm": "myers",
      "env_locks": {
        "LC_ALL": "C",
        "color": "off",
        "core.autocrlf": "false"
      },
      "checksum": "a825ee3c8a224346ffca3249e2076b04f5d0044f36e98b555463b80916859731"
    },
    "files": [
      {
        "status": "M",
        "path_old": "src/file.py",
        "path_new": "src/file.py",
        "mode_old": "100644",
        "mode_new": "100644",
        "size_old": 1234,
        "size_new": 1456,
        "is_binary": false,
        "is_submodule": false,
        "eol_only_change": false,
        "whitespace_only_change": false,
        "summarized": false,
        "truncated": false,
        "hunks": [
          {
            "header": "@@ -10,5 +10,6 @@",
            "old_start": 10,
            "old_lines": 5,
            "new_start": 10,
            "new_lines": 6,
            "added": 2,
            "deleted": 1,
            "patch": "@@ -10,5 +10,6 @@\n context\n-old line\n+new line\n+added line\n context"
          }
        ]
      }
    ],
    "omitted_files_count": 0,
    "notes": []
  }
}
```

**Error Response (4xx/5xx)**:
```json
{
  "ok": false,
  "error": {
    "code": "COMMIT_NOT_FOUND",
    "message": "Commits not found: abc123",
    "details": {
      "missing_commits": ["abc123"],
      "repo_url": "https://github.com/user/repo.git"
    }
  }
}
```

### 2. GET /health - Health Check

**URL**: `GET http://127.0.0.1:8000/health`

**Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "git_available": true,
  "git_version": "2.50.0"
}
```

### 3. GET /version - Version Information

**URL**: `GET http://127.0.0.1:8000/version`

**Response**:
```json
{
  "version": "1.0.0",
  "api_version": "v1",
  "git_version": "2.50.0",
  "supported_features": [
    "deterministic_output",
    "capacity_management",
    "rename_detection",
    "binary_detection",
    "submodule_detection"
  ]
}
```

### 4. GET / - API Information

**URL**: `GET http://127.0.0.1:8000/`

**Response**:
```json
{
  "name": "P1 Diff API",
  "version": "1.0.0",
  "description": "Deterministic Git diff ingestion API for MCP integration",
  "endpoints": {
    "diff": "POST /diff - Create deterministic diff",
    "health": "GET /health - Health check",
    "version": "GET /version - Version information",
    "docs": "GET /docs - API documentation"
  }
}
```

## Usage Examples

### Example 1: Basic Diff Request

```bash
# Using curl (Linux/macOS)
curl -X POST "http://127.0.0.1:8000/diff" \
  -H "Content-Type: application/json" \
  -d '{
    "repo_url": "https://github.com/presidioforts/direct-finetune-rag-model.git",
    "commit_good": "ba7765dd48c0ba51f4fd12cde48fd100aecdb743",
    "commit_candidate": "d7a39abec5a282b9955afdd1649a5f1bafae35f7",
    "branch_name": "codex/move-prompts-to-external-template-files"
  }'
```

```powershell
# Using PowerShell (Windows)
$body = @{
    repo_url = "https://github.com/presidioforts/direct-finetune-rag-model.git"
    commit_good = "ba7765dd48c0ba51f4fd12cde48fd100aecdb743"
    commit_candidate = "d7a39abec5a282b9955afdd1649a5f1bafae35f7"
    branch_name = "codex/move-prompts-to-external-template-files"
} | ConvertTo-Json

Invoke-WebRequest -Uri "http://127.0.0.1:8000/diff" -Method POST -Body $body -ContentType "application/json"
```

### Example 2: Python Requests

```python
import requests
import json

# Prepare request data
data = {
    "repo_url": "https://github.com/user/repo.git",
    "commit_good": "abc123def456",
    "commit_candidate": "def456abc123",
    "branch_name": "feature/new-feature",
    "cap_total": 1000000,
    "cap_file": 100000,
    "context_lines": 5
}

# Make request
response = requests.post('http://127.0.0.1:8000/diff', json=data)

if response.status_code == 200:
    result = response.json()
    if result['ok']:
        print(f"✅ Success! Files changed: {len(result['data']['files'])}")
        print(f"Checksum: {result['data']['provenance']['checksum']}")
    else:
        print(f"❌ Error: {result['error']['message']}")
else:
    print(f"❌ HTTP Error: {response.status_code}")
```

### Example 3: JavaScript/Node.js

```javascript
const axios = require('axios');

async function getDiff() {
  try {
    const response = await axios.post('http://127.0.0.1:8000/diff', {
      repo_url: 'https://github.com/user/repo.git',
      commit_good: 'abc123def456',
      commit_candidate: 'def456abc123',
      branch_name: 'feature/new-feature'
    });

    if (response.data.ok) {
      console.log('✅ Success!');
      console.log(`Files changed: ${response.data.data.files.length}`);
      console.log(`Checksum: ${response.data.data.provenance.checksum}`);
      return response.data;
    } else {
      console.log('❌ Error:', response.data.error.message);
    }
  } catch (error) {
    console.log('❌ Request failed:', error.message);
  }
}

getDiff();
```

## Response Data Structure

### File Status Codes

| Status | Description |
|--------|-------------|
| `A` | Added |
| `M` | Modified |
| `D` | Deleted |
| `R` | Renamed |
| `C` | Copied |
| `T` | Type changed |

### Error Codes

| Code | Description |
|------|-------------|
| `GIT_VERSION_UNSUPPORTED` | Git version < 2.30 |
| `CLONE_FAILED` | Repository clone failed |
| `COMMIT_NOT_FOUND` | One or more commits not found |
| `CAPS_INVALID` | Invalid capacity configuration |
| `NETWORK_TIMEOUT` | Network operation timed out |
| `INTERNAL_ERROR` | Unexpected server error |
| `VALIDATION_ERROR` | Request validation failed |

## MCP Integration

### For AI Agents

The API is designed specifically for MCP (Model Context Protocol) integration. AI agents can:

1. **Make HTTP POST requests** to `/diff` endpoint
2. **Receive complete diff analysis** in structured JSON format
3. **Send to LLMs** for code analysis, review, or insights
4. **Get deterministic results** - same inputs always produce identical output

### Example MCP Usage

```python
# AI Agent MCP call example
import requests

def analyze_code_changes(repo_url, base_commit, head_commit, branch=None):
    """Analyze code changes for LLM consumption."""
    
    # Request diff analysis
    response = requests.post('http://127.0.0.1:8000/diff', json={
        'repo_url': repo_url,
        'commit_good': base_commit,
        'commit_candidate': head_commit,
        'branch_name': branch
    })
    
    if response.status_code == 200:
        diff_data = response.json()
        
        if diff_data['ok']:
            # Send to LLM for analysis
            return send_to_llm_for_analysis(diff_data)
        else:
            return f"Error: {diff_data['error']['message']}"
    else:
        return f"HTTP Error: {response.status_code}"

def send_to_llm_for_analysis(diff_data):
    """Send diff data to LLM for code analysis."""
    # The diff_data contains complete information:
    # - File-by-file changes
    # - Line-by-line diffs
    # - Metadata and context
    # - Perfect for LLM analysis
    
    prompt = f"""
    Analyze these code changes:
    
    Repository: {diff_data['data']['provenance']['repo_url']}
    Files changed: {len(diff_data['data']['files'])}
    Branch: {diff_data['data']['provenance']['branch_name']}
    
    Detailed changes:
    {json.dumps(diff_data['data']['files'], indent=2)}
    
    Please provide:
    1. Summary of changes
    2. Potential impact analysis
    3. Code quality assessment
    4. Security considerations
    """
    
    # Send to your LLM service
    return llm_service.analyze(prompt)
```

## Server Configuration

### Command Line Options

```bash
python scripts/start_api.py [OPTIONS]

Options:
  --host TEXT          Host to bind to (default: 127.0.0.1)
  --port INTEGER       Port to bind to (default: 8000)
  --workers INTEGER    Number of worker processes (default: 1)
  --reload            Enable auto-reload for development
  --log-level TEXT    Log level: critical|error|warning|info|debug|trace
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `HOST` | Server host | 127.0.0.1 |
| `PORT` | Server port | 8000 |
| `WORKERS` | Worker processes | 1 |
| `LOG_LEVEL` | Logging level | info |

### Production Deployment

```bash
# Production server with multiple workers
python scripts/start_api.py --host 0.0.0.0 --port 8000 --workers 4 --log-level warning

# Using environment variables
export HOST=0.0.0.0
export PORT=8000
export WORKERS=4
export LOG_LEVEL=warning
python scripts/start_api.py
```

## Interactive Documentation

The API provides interactive documentation at:

- **Swagger UI**: `http://127.0.0.1:8000/docs`
- **ReDoc**: `http://127.0.0.1:8000/redoc`

These interfaces allow you to:
- Explore all endpoints
- Test requests directly in the browser
- View detailed request/response schemas
- Download OpenAPI specification

## Troubleshooting

### Common Issues

1. **Server won't start**
   ```bash
   # Check if port is in use
   netstat -an | findstr :8000
   
   # Use different port
   python scripts/start_api.py --port 8001
   ```

2. **Git version errors**
   ```bash
   # Check git version
   git --version
   
   # Ensure git >= 2.30
   ```

3. **Repository access errors**
   ```bash
   # Test repository access
   git ls-remote https://github.com/user/repo.git
   ```

4. **Python version issues**
   ```bash
   # Ensure Python 3.11+
   python --version
   
   # Activate correct virtual environment
   venv311\Scripts\Activate.ps1  # Windows
   source venv311/bin/activate   # Linux/macOS
   ```

### Debug Mode

```bash
# Start with debug logging
python scripts/start_api.py --log-level debug --reload

# Check server logs for detailed error information
```

## Performance Considerations

- **Response Time**: Typically 2-10 seconds depending on repository size
- **Memory Usage**: ~50-200MB per request depending on diff size
- **Concurrent Requests**: Supports multiple concurrent requests
- **Capacity Limits**: Configurable caps prevent excessive memory usage
- **Deterministic**: Same inputs always produce identical output with matching checksums

## Security Notes

- **Input Validation**: All inputs are validated using Pydantic models
- **Repository Access**: Only public repositories or accessible private repos
- **No Persistence**: No data is stored on the server
- **Temporary Workspaces**: Automatically cleaned up after processing
- **Rate Limiting**: Consider implementing rate limiting for production use

---

## Support

For issues, questions, or contributions:
- Check the main README.md for development setup
- Review the API documentation at `/docs`
- Test with the health endpoint first
- Ensure all prerequisites are met (Python 3.11+, Git 2.30+)
