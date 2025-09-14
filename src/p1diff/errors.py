"""Error definitions and handling for P1 Diff tool."""

from typing import Any, Dict, Optional


class P1DiffError(Exception):
    """Base exception for P1 Diff tool errors."""

    def __init__(self, code: str, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize error with code, message, and optional details."""
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON serialization."""
        result = {
            "code": self.code,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result


class GitVersionUnsupportedError(P1DiffError):
    """Git version is not supported."""

    def __init__(self, detected_version: str, required_version: str = "2.30"):
        super().__init__(
            code="GIT_VERSION_UNSUPPORTED",
            message=f"Git version {detected_version} is not supported. "
            f"Minimum required: {required_version}",
            details={
                "detected_version": detected_version,
                "required_version": required_version,
            },
        )


class CloneFailedError(P1DiffError):
    """Repository clone operation failed."""

    def __init__(self, repo_url: str, reason: str):
        super().__init__(
            code="CLONE_FAILED",
            message=f"Failed to clone repository: {reason}",
            details={"repo_url": repo_url, "reason": reason},
        )


class CommitNotFoundError(P1DiffError):
    """One or more commits not found in repository."""

    def __init__(self, missing_commits: list[str], repo_url: str):
        super().__init__(
            code="COMMIT_NOT_FOUND",
            message=f"Commits not found: {', '.join(missing_commits)}",
            details={"missing_commits": missing_commits, "repo_url": repo_url},
        )


class CapsInvalidError(P1DiffError):
    """Invalid capacity configuration."""

    def __init__(self, reason: str):
        super().__init__(
            code="CAPS_INVALID",
            message=f"Invalid capacity configuration: {reason}",
            details={"reason": reason},
        )


class NetworkTimeoutError(P1DiffError):
    """Network operation timed out."""

    def __init__(self, operation: str, timeout_seconds: int):
        super().__init__(
            code="NETWORK_TIMEOUT",
            message=f"Network timeout during {operation} after {timeout_seconds}s",
            details={"operation": operation, "timeout_seconds": timeout_seconds},
        )
