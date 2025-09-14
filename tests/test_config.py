"""Tests for configuration module."""

import pytest

from p1diff.config import DiffConfig
from p1diff.errors import CapsInvalidError


class TestDiffConfig:
    """Test DiffConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = DiffConfig(
            repo_url="https://example.com/repo.git",
            commit_good="abc123",
            commit_candidate="def456",
        )

        assert config.repo_url == "https://example.com/repo.git"
        assert config.commit_good == "abc123"
        assert config.commit_candidate == "def456"
        assert config.branch_name is None
        assert config.cap_total == 800_000
        assert config.cap_file == 64_000
        assert config.context_lines == 3
        assert config.find_renames_threshold == 90
        assert config.json_output_path is None
        assert config.keep_workdir is False
        assert config.keep_on_error is False
        assert config.diff_algorithm == "myers"

    def test_custom_config(self):
        """Test custom configuration values."""
        config = DiffConfig(
            repo_url="https://example.com/repo.git",
            commit_good="abc123",
            commit_candidate="def456",
            branch_name="feature-branch",
            cap_total=1_000_000,
            cap_file=100_000,
            context_lines=5,
            find_renames_threshold=80,
            json_output_path="output.json",
            keep_workdir=True,
            keep_on_error=True,
        )

        assert config.branch_name == "feature-branch"
        assert config.cap_total == 1_000_000
        assert config.cap_file == 100_000
        assert config.context_lines == 5
        assert config.find_renames_threshold == 80
        assert config.json_output_path == "output.json"
        assert config.keep_workdir is True
        assert config.keep_on_error is True

    def test_validation_negative_cap_total(self):
        """Test validation of negative cap_total."""
        with pytest.raises(ValueError, match="cap_total must be positive"):
            DiffConfig(
                repo_url="https://example.com/repo.git",
                commit_good="abc123",
                commit_candidate="def456",
                cap_total=-1,
            )

    def test_validation_negative_cap_file(self):
        """Test validation of negative cap_file."""
        with pytest.raises(ValueError, match="cap_file must be positive"):
            DiffConfig(
                repo_url="https://example.com/repo.git",
                commit_good="abc123",
                commit_candidate="def456",
                cap_file=-1,
            )

    def test_validation_cap_file_exceeds_total(self):
        """Test validation when cap_file exceeds cap_total."""
        with pytest.raises(ValueError, match="cap_file cannot exceed cap_total"):
            DiffConfig(
                repo_url="https://example.com/repo.git",
                commit_good="abc123",
                commit_candidate="def456",
                cap_total=100,
                cap_file=200,
            )

    def test_validation_negative_context_lines(self):
        """Test validation of negative context_lines."""
        with pytest.raises(ValueError, match="context_lines cannot be negative"):
            DiffConfig(
                repo_url="https://example.com/repo.git",
                commit_good="abc123",
                commit_candidate="def456",
                context_lines=-1,
            )

    def test_validation_invalid_rename_threshold(self):
        """Test validation of invalid rename threshold."""
        with pytest.raises(ValueError, match="find_renames_threshold must be between 0 and 100"):
            DiffConfig(
                repo_url="https://example.com/repo.git",
                commit_good="abc123",
                commit_candidate="def456",
                find_renames_threshold=150,
            )

    def test_git_env(self):
        """Test git environment variables."""
        config = DiffConfig(
            repo_url="https://example.com/repo.git",
            commit_good="abc123",
            commit_candidate="def456",
        )

        env = config.git_env
        assert env["LC_ALL"] == "C"
        assert env["GIT_CONFIG_GLOBAL"] == "/dev/null"
        assert env["GIT_CONFIG_SYSTEM"] == "/dev/null"
        assert env["GIT_TERMINAL_PROMPT"] == "0"
        assert env["GIT_ASKPASS"] == "echo"
        assert env["SSH_ASKPASS"] == "echo"
        assert env["GCM_INTERACTIVE"] == "never"

    def test_to_provenance_dict(self):
        """Test conversion to provenance dictionary."""
        config = DiffConfig(
            repo_url="https://example.com/repo.git",
            commit_good="abc123",
            commit_candidate="def456",
            branch_name="feature-branch",
            cap_total=1_000_000,
            cap_file=100_000,
            context_lines=5,
            find_renames_threshold=80,
        )

        provenance = config.to_provenance_dict()

        assert provenance["repo_url"] == "https://example.com/repo.git"
        assert provenance["commit_good"] == "abc123"
        assert provenance["commit_candidate"] == "def456"
        assert provenance["branch_name"] == "feature-branch"
        assert provenance["caps"]["total_bytes"] == 1_000_000
        assert provenance["caps"]["per_file_bytes"] == 100_000
        assert provenance["caps"]["context_lines"] == 5
        assert provenance["rename_detection"]["enabled"] is True
        assert provenance["rename_detection"]["threshold_pct"] == 80
        assert provenance["diff_algorithm"] == "myers"
        assert provenance["env_locks"]["LC_ALL"] == "C"
        assert provenance["env_locks"]["color"] == "off"
        assert provenance["env_locks"]["core.autocrlf"] == "false"
