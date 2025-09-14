# P1 Diff Ingestion Tool

A deterministic Git diff ingestion tool that produces stable JSON output for code analysis workflows.

## Overview

P1 Diff is a production-ready CLI tool that takes a repository URL and two commit SHAs, clones the repository to a temporary workspace, computes deterministic per-file unified diffs with strict byte caps, and outputs a stable JSON payload for downstream analysis.

### Key Features

- **Deterministic Output**: Same inputs always produce byte-identical JSON with matching checksums
- **Capacity Management**: Configurable per-file (64KB) and total (800KB) caps with intelligent truncation
- **Rename Detection**: 90% threshold with deterministic tie-breaking
- **Special File Handling**: Lockfiles and generated files are summarized when oversized
- **Binary/Submodule Safety**: Metadata-only output, no raw blob content
- **Production Ready**: Comprehensive error handling, signal-safe cleanup, extensive test coverage

## Installation

### Requirements

- Python 3.11 or higher
- Git 2.30 or higher

### Install from Source

```bash
git clone <repository-url>
cd PR-Diff-Ingestion
make install-dev
```

### Install for Production

```bash
pip install -e .
```

## Usage

### Basic Usage

```bash
p1diff --repo https://github.com/user/repo.git --good abc123 --cand def456
```

### Full Options

```bash
p1diff --repo <url> --good <sha> --cand <sha> \
       [--branch <name>] \
       [--cap-total 800000] [--cap-file 64000] [--context 3] \
       [--find-renames 90] \
       [--json out.json] \
       [--keep-workdir] [--keep-on-error]
```

### Options

- `--repo`: Repository URL or local path (required)
- `--good`: Good commit SHA (baseline) (required)  
- `--cand`: Candidate commit SHA (comparison target) (required)
- `--branch`: Branch name (for metadata and fetch hint)
- `--cap-total`: Total capacity limit in bytes (default: 800000)
- `--cap-file`: Per-file capacity limit in bytes (default: 64000)
- `--context`: Number of context lines in diffs (default: 3)
- `--find-renames`: Rename detection threshold percentage (default: 90)
- `--json`: Output JSON to file instead of stdout
- `--keep-workdir`: Keep temporary work directory for debugging
- `--keep-on-error`: Keep work directory on error for debugging

### Examples

```bash
# Basic diff between two commits
p1diff --repo https://github.com/user/repo.git --good v1.0.0 --cand v2.0.0

# Save output to file with custom caps
p1diff --repo /path/to/local/repo --good abc123 --cand def456 \
       --cap-total 1000000 --cap-file 100000 --json output.json

# Debug mode with preserved workspace
p1diff --repo https://github.com/user/repo.git --good abc123 --cand def456 \
       --keep-workdir --keep-on-error
```

## Usage Guide

This section provides step-by-step instructions for testing and using the P1 Diff tool with real repositories.

### Prerequisites

1. **Environment Setup**
   ```bash
   # Ensure you're in the project directory
   cd C:\Users\krish\AIDevWorkspace\PR-Diff-Ingestion
   
   # Activate virtual environment (Windows)
   venv311\Scripts\Activate.ps1
   
   # Verify Python version
   python --version  # Should show Python 3.11+
   ```

2. **Verify Installation**
   ```bash
   # Check if the tool is properly installed
   python -m p1diff.main --help
   ```

### Testing with Real Repository

Here's a complete example using a real repository:

**Repository**: `https://github.com/presidioforts/direct-finetune-rag-model.git`
**Baseline Commit**: `ba7765dd48c0ba51f4fd12cde48fd100aecdb743`
**Candidate Commit**: `d7a39abec5a282b9955afdd1649a5f1bafae35f7`
**Branch**: `codex/move-prompts-to-external-template-files`

#### Step 1: Basic Test
```bash
python -m p1diff.main \
  --repo https://github.com/presidioforts/direct-finetune-rag-model.git \
  --good ba7765dd48c0ba51f4fd12cde48fd100aecdb743 \
  --cand d7a39abec5a282b9955afdd1649a5f1bafae35f7 \
  --branch codex/move-prompts-to-external-template-files
```

#### Step 2: Save Output to File
```bash
python -m p1diff.main \
  --repo https://github.com/presidioforts/direct-finetune-rag-model.git \
  --good ba7765dd48c0ba51f4fd12cde48fd100aecdb743 \
  --cand d7a39abec5a282b9955afdd1649a5f1bafae35f7 \
  --branch codex/move-prompts-to-external-template-files \
  --json test_output.json
```

#### Step 3: Verify Output
```bash
# Check if file was created
ls test_output.json

# View first 20 lines of JSON output
Get-Content test_output.json | Select-Object -First 20

# Check file size
(Get-Item test_output.json).Length
```

#### Step 4: Test Determinism
```bash
# Run the same command twice with different output files
python -m p1diff.main \
  --repo https://github.com/presidioforts/direct-finetune-rag-model.git \
  --good ba7765dd48c0ba51f4fd12cde48fd100aecdb743 \
  --cand d7a39abec5a282b9955afdd1649a5f1bafae35f7 \
  --branch codex/move-prompts-to-external-template-files \
  --json output1.json

python -m p1diff.main \
  --repo https://github.com/presidioforts/direct-finetune-rag-model.git \
  --good ba7765dd48c0ba51f4fd12cde48fd100aecdb743 \
  --cand d7a39abec5a282b9955afdd1649a5f1bafae35f7 \
  --branch codex/move-prompts-to-external-template-files \
  --json output2.json

# Compare checksums (should be identical)
python -c "
import json
with open('output1.json') as f1, open('output2.json') as f2:
    data1 = json.load(f1)
    data2 = json.load(f2)
    checksum1 = data1['data']['provenance']['checksum']
    checksum2 = data2['data']['provenance']['checksum']
    print(f'Checksum 1: {checksum1}')
    print(f'Checksum 2: {checksum2}')
    print(f'Deterministic: {checksum1 == checksum2}')
"
```

#### Step 5: Test Capacity Management
```bash
# Test with smaller caps to see truncation in action
python -m p1diff.main \
  --repo https://github.com/presidioforts/direct-finetune-rag-model.git \
  --good ba7765dd48c0ba51f4fd12cde48fd100aecdb743 \
  --cand d7a39abec5a282b9955afdd1649a5f1bafae35f7 \
  --branch codex/move-prompts-to-external-template-files \
  --cap-total 50000 --cap-file 10000 \
  --json small_caps.json
```

#### Step 6: Debug Mode
```bash
# Test with workspace preservation for debugging
python -m p1diff.main \
  --repo https://github.com/presidioforts/direct-finetune-rag-model.git \
  --good ba7765dd48c0ba51f4fd12cde48fd100aecdb743 \
  --cand d7a39abec5a282b9955afdd1649a5f1bafae35f7 \
  --branch codex/move-prompts-to-external-template-files \
  --keep-workdir --json debug_output.json
```

#### Step 7: Analyze Results
```bash
# Parse and analyze the JSON output
python -c "
import json
with open('test_output.json') as f:
    data = json.load(f)
    
if data['ok']:
    payload = data['data']
    print(f'✅ Success!')
    print(f'Repository: {payload[\"provenance\"][\"repo_url\"]}')
    print(f'Files changed: {len(payload[\"files\"])}')
    print(f'Omitted files: {payload[\"omitted_files_count\"]}')
    print(f'Git version: {payload[\"provenance\"][\"git_version\"]}')
    print(f'Checksum: {payload[\"provenance\"][\"checksum\"]}')
    print(f'Notes: {payload[\"notes\"]}')
    
    # Show file types
    statuses = {}
    for file in payload['files']:
        status = file['status']
        statuses[status] = statuses.get(status, 0) + 1
    print(f'File changes by type: {statuses}')
else:
    print(f'❌ Error: {data[\"error\"][\"code\"]} - {data[\"error\"][\"message\"]}')
"
```

#### Step 8: Performance Test
```bash
# Measure execution time (PowerShell)
Measure-Command { 
  python -m p1diff.main \
    --repo https://github.com/presidioforts/direct-finetune-rag-model.git \
    --good ba7765dd48c0ba51f4fd12cde48fd100aecdb743 \
    --cand d7a39abec5a282b9955afdd1649a5f1bafae35f7 \
    --branch codex/move-prompts-to-external-template-files \
    --json perf_test.json 
}
```

### Common Use Cases

#### 1. Code Review Analysis
```bash
# Generate diff for code review
p1diff --repo https://github.com/user/repo.git \
       --good main --cand feature-branch \
       --json code_review.json
```

#### 2. Release Comparison
```bash
# Compare two release tags
p1diff --repo https://github.com/user/repo.git \
       --good v1.0.0 --cand v2.0.0 \
       --cap-total 2000000 --json release_diff.json
```

#### 3. Local Repository Analysis
```bash
# Analyze local repository changes
p1diff --repo /path/to/local/repo \
       --good HEAD~5 --cand HEAD \
       --json local_changes.json
```

#### 4. Large Repository with Custom Settings
```bash
# Handle large repositories with custom caps and rename detection
p1diff --repo https://github.com/large/repo.git \
       --good abc123 --cand def456 \
       --cap-total 5000000 --cap-file 200000 \
       --find-renames 80 --context 5 \
       --json large_repo.json
```

### Validation Checklist

When testing, verify these key aspects:

- [ ] **Success Response**: JSON contains `"ok": true`
- [ ] **Deterministic Output**: Same checksum across multiple runs
- [ ] **File Changes**: Actual changes between commits are captured
- [ ] **Capacity Management**: Truncation works with small caps
- [ ] **Performance**: Completes in reasonable time (< 30s for most repos)
- [ ] **Git Version**: Shows your local git version (≥2.30)
- [ ] **Error Handling**: Graceful handling of invalid inputs

### Troubleshooting

#### Common Issues

1. **Network Errors**
   ```bash
   # Check internet connection and repository access
   git ls-remote https://github.com/user/repo.git
   ```

2. **Git Version Errors**
   ```bash
   # Ensure git ≥2.30 is installed
   git --version
   ```

3. **Permission Errors**
   ```bash
   # Verify repository access
   git clone https://github.com/user/repo.git temp_test
   rm -rf temp_test
   ```

4. **Memory Issues**
   ```bash
   # Try with smaller caps first
   p1diff --repo <url> --good <sha> --cand <sha> \
          --cap-total 100000 --cap-file 10000
   ```

#### Debug Mode

For troubleshooting, use debug flags:
```bash
p1diff --repo <url> --good <sha> --cand <sha> \
       --keep-workdir --keep-on-error --json debug.json
```

This preserves the temporary workspace for manual inspection.

## Output Format

The tool outputs JSON with a consistent envelope structure:

### Success Response

```json
{
  "ok": true,
  "data": {
    "provenance": {
      "repo_url": "https://github.com/user/repo.git",
      "commit_good": "abc123...",
      "commit_candidate": "def456...",
      "branch_name": "feature-branch",
      "caps": {
        "total_bytes": 800000,
        "per_file_bytes": 64000,
        "context_lines": 3
      },
      "rename_detection": {
        "enabled": true,
        "threshold_pct": 90
      },
      "git_version": "2.34.1",
      "diff_algorithm": "myers",
      "env_locks": {
        "LC_ALL": "C",
        "color": "off",
        "core.autocrlf": "false"
      },
      "checksum": "sha256-hash-of-payload"
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

### Error Response

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

### File Status Codes

- `A`: Added
- `M`: Modified  
- `D`: Deleted
- `R`: Renamed
- `C`: Copied
- `T`: Type changed

### Error Codes

- `GIT_VERSION_UNSUPPORTED`: Git version < 2.30
- `CLONE_FAILED`: Repository clone failed
- `COMMIT_NOT_FOUND`: One or more commits not found
- `CAPS_INVALID`: Invalid capacity configuration
- `NETWORK_TIMEOUT`: Network operation timed out

## Development

### Project Structure

```
PR-Diff-Ingestion/
├── src/p1diff/           # Main package
│   ├── __init__.py       # Package initialization
│   ├── main.py           # CLI entry point and orchestration
│   ├── config.py         # Configuration management
│   ├── vcs.py            # Git operations and repository handling
│   ├── diffpack.py       # Diff processing and hunk splitting
│   ├── caps.py           # Capacity management and truncation
│   ├── serialize.py      # Deterministic JSON serialization
│   ├── policies.py       # File type policies and detection
│   └── errors.py         # Error definitions and handling
├── tests/                # Test suite
│   ├── conftest.py       # Test fixtures and configuration
│   ├── test_*.py         # Unit tests for each module
│   └── test_integration.py # Integration tests
├── docs/                 # Documentation
├── scripts/              # Utility scripts
├── pyproject.toml        # Project configuration
├── requirements*.txt     # Dependencies
├── Makefile             # Development commands
└── README.md            # This file
```

### Development Setup

```bash
# Clone repository
git clone <repository-url>
cd PR-Diff-Ingestion

# Set up development environment
make dev-setup

# Run tests
make test

# Run linting and type checking
make check

# Format code
make format
```

### Testing

```bash
# Run all tests
make test

# Run unit tests only
make test-unit

# Run integration tests (requires network)
make test-integration

# Run with coverage
make test-coverage
```

### Architecture

The tool follows a modular architecture with clear separation of concerns:

1. **CLI Layer** (`main.py`): Argument parsing, orchestration, and output formatting
2. **VCS Layer** (`vcs.py`): Git operations, cloning, and change discovery
3. **Processing Layer** (`diffpack.py`): Diff parsing and hunk extraction
4. **Policy Layer** (`caps.py`, `policies.py`): Capacity management and file type handling
5. **Serialization Layer** (`serialize.py`): Deterministic JSON output
6. **Configuration Layer** (`config.py`): Settings and validation
7. **Error Layer** (`errors.py`): Structured error handling

### Key Design Principles

- **Determinism**: Same inputs always produce identical output
- **Safety**: No raw blob content, signal-safe cleanup
- **Performance**: Minimal clones, efficient processing
- **Reliability**: Comprehensive error handling and validation
- **Maintainability**: Clear module boundaries, extensive tests

## License

MIT License - see LICENSE file for details.
