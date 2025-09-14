"""Tests for main CLI module."""

import json
import sys
from unittest.mock import patch

import pytest

from p1diff.main import create_config, create_parser, main, validate_args


class TestCLI:
    """Test CLI functionality."""

    def test_create_parser(self):
        """Test argument parser creation."""
        parser = create_parser()
        
        # Test required arguments
        with pytest.raises(SystemExit):
            parser.parse_args([])

        # Test valid arguments
        args = parser.parse_args([
            "--repo", "https://example.com/repo.git",
            "--good", "abc123",
            "--cand", "def456",
        ])

        assert args.repo == "https://example.com/repo.git"
        assert args.good == "abc123"
        assert args.cand == "def456"

    def test_create_parser_with_optional_args(self):
        """Test parser with optional arguments."""
        parser = create_parser()
        args = parser.parse_args([
            "--repo", "https://example.com/repo.git",
            "--good", "abc123",
            "--cand", "def456",
            "--branch", "feature-branch",
            "--cap-total", "1000000",
            "--cap-file", "100000",
            "--context", "5",
            "--find-renames", "80",
            "--json", "output.json",
            "--keep-workdir",
            "--keep-on-error",
        ])

        assert args.branch == "feature-branch"
        assert args.cap_total == 1000000
        assert args.cap_file == 100000
        assert args.context == 5
        assert args.find_renames == 80
        assert args.json == "output.json"
        assert args.keep_workdir is True
        assert args.keep_on_error is True

    def test_validate_args_valid(self):
        """Test argument validation with valid args."""
        parser = create_parser()
        args = parser.parse_args([
            "--repo", "https://example.com/repo.git",
            "--good", "abc123",
            "--cand", "def456",
        ])

        # Should not raise
        validate_args(args)

    def test_validate_args_invalid_cap_total(self):
        """Test validation with invalid cap_total."""
        parser = create_parser()
        args = parser.parse_args([
            "--repo", "https://example.com/repo.git",
            "--good", "abc123",
            "--cand", "def456",
            "--cap-total", "-1",
        ])

        with pytest.raises(ValueError, match="--cap-total must be positive"):
            validate_args(args)

    def test_validate_args_invalid_cap_file(self):
        """Test validation with invalid cap_file."""
        parser = create_parser()
        args = parser.parse_args([
            "--repo", "https://example.com/repo.git",
            "--good", "abc123",
            "--cand", "def456",
            "--cap-file", "-1",
        ])

        with pytest.raises(ValueError, match="--cap-file must be positive"):
            validate_args(args)

    def test_validate_args_cap_file_exceeds_total(self):
        """Test validation when cap_file exceeds cap_total."""
        parser = create_parser()
        args = parser.parse_args([
            "--repo", "https://example.com/repo.git",
            "--good", "abc123",
            "--cand", "def456",
            "--cap-total", "100",
            "--cap-file", "200",
        ])

        with pytest.raises(ValueError, match="--cap-file cannot exceed --cap-total"):
            validate_args(args)

    def test_validate_args_invalid_context(self):
        """Test validation with invalid context."""
        parser = create_parser()
        args = parser.parse_args([
            "--repo", "https://example.com/repo.git",
            "--good", "abc123",
            "--cand", "def456",
            "--context", "-1",
        ])

        with pytest.raises(ValueError, match="--context cannot be negative"):
            validate_args(args)

    def test_validate_args_invalid_find_renames(self):
        """Test validation with invalid find_renames."""
        parser = create_parser()
        args = parser.parse_args([
            "--repo", "https://example.com/repo.git",
            "--good", "abc123",
            "--cand", "def456",
            "--find-renames", "150",
        ])

        with pytest.raises(ValueError, match="--find-renames must be between 0 and 100"):
            validate_args(args)

    def test_create_config(self):
        """Test config creation from args."""
        parser = create_parser()
        args = parser.parse_args([
            "--repo", "https://example.com/repo.git",
            "--good", "abc123",
            "--cand", "def456",
            "--branch", "feature-branch",
            "--cap-total", "1000000",
            "--cap-file", "100000",
            "--context", "5",
            "--find-renames", "80",
            "--json", "output.json",
            "--keep-workdir",
            "--keep-on-error",
        ])

        config = create_config(args)

        assert config.repo_url == "https://example.com/repo.git"
        assert config.commit_good == "abc123"
        assert config.commit_candidate == "def456"
        assert config.branch_name == "feature-branch"
        assert config.cap_total == 1000000
        assert config.cap_file == 100000
        assert config.context_lines == 5
        assert config.find_renames_threshold == 80
        assert config.json_output_path == "output.json"
        assert config.keep_workdir is True
        assert config.keep_on_error is True

    @patch('p1diff.main.process_diff')
    def test_main_success(self, mock_process_diff, capsys):
        """Test successful main execution."""
        # Mock the process_diff function
        mock_payload = {
            "provenance": {"checksum": "test123"},
            "files": [],
            "omitted_files_count": 0,
            "notes": [],
        }
        mock_process_diff.return_value = mock_payload

        test_args = [
            "p1diff",
            "--repo", "https://example.com/repo.git",
            "--good", "abc123",
            "--cand", "def456",
        ]

        with patch.object(sys, 'argv', test_args):
            exit_code = main()

        assert exit_code == 0

        # Check output
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["ok"] is True
        assert "data" in output

    @patch('p1diff.main.validate_args')
    def test_main_validation_error(self, mock_validate, capsys):
        """Test main with validation error."""
        mock_validate.side_effect = ValueError("Invalid argument")

        test_args = [
            "p1diff",
            "--repo", "https://example.com/repo.git",
            "--good", "abc123",
            "--cand", "def456",
        ]

        with patch.object(sys, 'argv', test_args):
            exit_code = main()

        assert exit_code == 1

        # Check error output
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["ok"] is False
        assert output["error"]["code"] == "INTERNAL_ERROR"
