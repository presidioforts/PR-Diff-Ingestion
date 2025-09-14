"""Configuration management for P1 Diff tool."""

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class DiffConfig:
    """Configuration for diff generation and processing."""

    # Required parameters
    repo_url: str
    commit_good: str
    commit_candidate: str

    # Optional parameters
    branch_name: Optional[str] = None

    # Caps (in bytes)
    cap_total: int = 800_000  # 800 KB
    cap_file: int = 64_000  # 64 KB
    context_lines: int = 3

    # Rename detection
    find_renames_threshold: int = 90  # percentage

    # Output options
    json_output_path: Optional[str] = None

    # Workspace options
    keep_workdir: bool = False
    keep_on_error: bool = False

    # Git environment settings
    diff_algorithm: str = "myers"

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if self.cap_total <= 0:
            raise ValueError("cap_total must be positive")
        if self.cap_file <= 0:
            raise ValueError("cap_file must be positive")
        if self.cap_file > self.cap_total:
            raise ValueError("cap_file cannot exceed cap_total")
        if self.context_lines < 0:
            raise ValueError("context_lines cannot be negative")
        if not (0 <= self.find_renames_threshold <= 100):
            raise ValueError("find_renames_threshold must be between 0 and 100")

    @property
    def git_env(self) -> Dict[str, str]:
        """Get Git environment variables for deterministic output."""
        env = os.environ.copy()
        
        # Use platform-appropriate null device
        null_device = "NUL" if os.name == "nt" else "/dev/null"
        
        env.update(
            {
                "LC_ALL": "C",
                "GIT_CONFIG_GLOBAL": null_device,
                "GIT_CONFIG_SYSTEM": null_device,
                "GIT_TERMINAL_PROMPT": "0",
                "GIT_ASKPASS": "echo",
                "SSH_ASKPASS": "echo",
                "GCM_INTERACTIVE": "never",
            }
        )
        return env

    def to_provenance_dict(self) -> Dict[str, Any]:
        """Convert config to provenance dictionary for output."""
        return {
            "repo_url": self.repo_url,
            "commit_good": self.commit_good,
            "commit_candidate": self.commit_candidate,
            "branch_name": self.branch_name,
            "caps": {
                "total_bytes": self.cap_total,
                "per_file_bytes": self.cap_file,
                "context_lines": self.context_lines,
            },
            "rename_detection": {
                "enabled": True,
                "threshold_pct": self.find_renames_threshold,
            },
            "diff_algorithm": self.diff_algorithm,
            "env_locks": {
                "LC_ALL": "C",
                "color": "off",
                "core.autocrlf": "false",
            },
        }
