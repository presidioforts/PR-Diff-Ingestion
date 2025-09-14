"""Pytest configuration and fixtures for P1 Diff tests."""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Generator

import pytest


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    temp_path = Path(tempfile.mkdtemp(prefix="p1diff_test_"))
    try:
        yield temp_path
    finally:
        if temp_path.exists():
            shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def git_repo(temp_dir: Path) -> Generator[Path, None, None]:
    """Create a temporary git repository for testing."""
    repo_path = temp_dir / "test_repo"
    repo_path.mkdir()

    # Initialize git repo
    env = os.environ.copy()
    env.update({
        "GIT_AUTHOR_NAME": "Test User",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test User",
        "GIT_COMMITTER_EMAIL": "test@example.com",
    })

    def run_git(args: list[str]) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git"] + args,
            cwd=repo_path,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )

    # Initialize repository
    run_git(["init"])
    run_git(["config", "user.name", "Test User"])
    run_git(["config", "user.email", "test@example.com"])

    # Create initial commit
    (repo_path / "README.md").write_text("# Test Repository\n")
    run_git(["add", "README.md"])
    run_git(["commit", "-m", "Initial commit"])

    yield repo_path


class GitRepoHelper:
    """Helper class for git repository operations in tests."""

    def __init__(self, repo_path: Path):
        self.repo_path = repo_path
        self.env = os.environ.copy()
        self.env.update({
            "GIT_AUTHOR_NAME": "Test User",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test User",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        })

    def run_git(self, args: list[str]) -> subprocess.CompletedProcess:
        """Run git command in the repository."""
        return subprocess.run(
            ["git"] + args,
            cwd=self.repo_path,
            env=self.env,
            check=True,
            capture_output=True,
            text=True,
        )

    def create_file(self, path: str, content: str) -> None:
        """Create a file with content."""
        file_path = self.repo_path / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)

    def modify_file(self, path: str, content: str) -> None:
        """Modify an existing file."""
        self.create_file(path, content)

    def delete_file(self, path: str) -> None:
        """Delete a file."""
        file_path = self.repo_path / path
        if file_path.exists():
            file_path.unlink()

    def add_and_commit(self, message: str, files: list[str] = None) -> str:
        """Add files and create a commit, return commit SHA."""
        if files:
            for file in files:
                self.run_git(["add", file])
        else:
            self.run_git(["add", "-A"])

        self.run_git(["commit", "-m", message])
        result = self.run_git(["rev-parse", "HEAD"])
        return result.stdout.strip()

    def get_current_sha(self) -> str:
        """Get current commit SHA."""
        result = self.run_git(["rev-parse", "HEAD"])
        return result.stdout.strip()

    def create_binary_file(self, path: str) -> None:
        """Create a binary file."""
        file_path = self.repo_path / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        # Create a simple binary file (PNG header)
        binary_content = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        file_path.write_bytes(binary_content)


@pytest.fixture
def git_helper(git_repo: Path) -> GitRepoHelper:
    """Create a git repository helper."""
    return GitRepoHelper(git_repo)
