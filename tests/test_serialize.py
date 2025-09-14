"""Tests for serialization module."""

import json

import pytest

from p1diff.config import DiffConfig
from p1diff.diffpack import DiffHunk, ProcessedFile
from p1diff.serialize import DeterministicSerializer


class TestDeterministicSerializer:
    """Test DeterministicSerializer class."""

    def test_serialize_file_basic(self):
        """Test basic file serialization."""
        config = DiffConfig("repo", "good", "cand")
        serializer = DeterministicSerializer(config)

        file = ProcessedFile(
            status="M",
            path_old="test.py",
            path_new="test.py",
            rename_score=None,
            rename_tiebreaker=None,
            mode_old="100644",
            mode_new="100644",
            size_old=100,
            size_new=120,
            is_binary=False,
            is_submodule=False,
        )

        result = serializer._serialize_file(file)

        assert result["status"] == "M"
        assert result["path_old"] == "test.py"
        assert result["path_new"] == "test.py"
        assert result["mode_old"] == "100644"
        assert result["mode_new"] == "100644"
        assert result["size_old"] == 100
        assert result["size_new"] == 120
        assert result["is_binary"] is False
        assert result["is_submodule"] is False

    def test_serialize_file_with_rename(self):
        """Test file serialization with rename information."""
        config = DiffConfig("repo", "good", "cand")
        serializer = DeterministicSerializer(config)

        file = ProcessedFile(
            status="R",
            path_old="old_name.py",
            path_new="new_name.py",
            rename_score=95,
            rename_tiebreaker="path",
            mode_old="100644",
            mode_new="100644",
            size_old=100,
            size_new=100,
            is_binary=False,
            is_submodule=False,
        )

        result = serializer._serialize_file(file)

        assert result["status"] == "R"
        assert result["path_old"] == "old_name.py"
        assert result["path_new"] == "new_name.py"
        assert result["rename_score"] == 95
        assert result["rename_tiebreaker"] == "path"

    def test_serialize_file_with_flags(self):
        """Test file serialization with various flags."""
        config = DiffConfig("repo", "good", "cand")
        serializer = DeterministicSerializer(config)

        file = ProcessedFile(
            status="M",
            path_old="test.py",
            path_new="test.py",
            rename_score=None,
            rename_tiebreaker=None,
            mode_old="100644",
            mode_new="100644",
            size_old=100,
            size_new=120,
            is_binary=False,
            is_submodule=False,
            eol_only_change=True,
            whitespace_only_change=False,
            summarized=True,
            truncated=False,
            omitted_hunks_count=5,
        )

        result = serializer._serialize_file(file)

        assert result["eol_only_change"] is True
        assert "whitespace_only_change" not in result  # False values not included
        assert result["summarized"] is True
        assert "truncated" not in result  # False values not included
        assert result["omitted_hunks_count"] == 5

    def test_serialize_file_with_submodule(self):
        """Test file serialization with submodule data."""
        config = DiffConfig("repo", "good", "cand")
        serializer = DeterministicSerializer(config)

        file = ProcessedFile(
            status="M",
            path_old="submodule",
            path_new="submodule",
            rename_score=None,
            rename_tiebreaker=None,
            mode_old="160000",
            mode_new="160000",
            size_old=None,
            size_new=None,
            is_binary=False,
            is_submodule=True,
            submodule={"old_sha": "abc123", "new_sha": "def456"},
        )

        result = serializer._serialize_file(file)

        assert result["is_submodule"] is True
        assert result["submodule"] == {"old_sha": "abc123", "new_sha": "def456"}

    def test_serialize_file_with_hunks(self):
        """Test file serialization with hunks."""
        config = DiffConfig("repo", "good", "cand")
        serializer = DeterministicSerializer(config)

        hunk1 = DiffHunk(
            header="@@ -1,1 +1,1 @@",
            old_start=1,
            old_lines=1,
            new_start=1,
            new_lines=1,
            added=1,
            deleted=1,
            patch="@@ -1,1 +1,1 @@\n-old\n+new",
        )

        hunk2 = DiffHunk(
            header="@@ -5,1 +5,1 @@",
            old_start=5,
            old_lines=1,
            new_start=5,
            new_lines=1,
            added=1,
            deleted=1,
            patch="@@ -5,1 +5,1 @@\n-old2\n+new2",
        )

        file = ProcessedFile(
            status="M",
            path_old="test.py",
            path_new="test.py",
            rename_score=None,
            rename_tiebreaker=None,
            mode_old="100644",
            mode_new="100644",
            size_old=100,
            size_new=120,
            is_binary=False,
            is_submodule=False,
            hunks=[hunk2, hunk1],  # Intentionally out of order
        )

        result = serializer._serialize_file(file)

        assert "hunks" in result
        hunks = result["hunks"]
        assert len(hunks) == 2

        # Should be sorted by position
        assert hunks[0]["old_start"] == 1
        assert hunks[1]["old_start"] == 5

        # Check hunk structure
        assert hunks[0]["header"] == "@@ -1,1 +1,1 @@"
        assert hunks[0]["old_lines"] == 1
        assert hunks[0]["new_lines"] == 1
        assert hunks[0]["added"] == 1
        assert hunks[0]["deleted"] == 1
        assert hunks[0]["patch"] == "@@ -1,1 +1,1 @@\n-old\n+new"

    def test_file_sort_key(self):
        """Test file sorting key generation."""
        config = DiffConfig("repo", "good", "cand")
        serializer = DeterministicSerializer(config)

        file1_data = {"path_new": "b.py", "status": "M"}
        file2_data = {"path_new": "a.py", "status": "M"}
        file3_data = {"path_old": "c.py", "path_new": None, "status": "D"}

        key1 = serializer._file_sort_key(file1_data)
        key2 = serializer._file_sort_key(file2_data)
        key3 = serializer._file_sort_key(file3_data)

        assert key2 < key1  # a.py < b.py
        assert key1 < key3  # b.py < c.py

    def test_serialize_output_complete(self):
        """Test complete output serialization."""
        config = DiffConfig(
            repo_url="https://example.com/repo.git",
            commit_good="abc123",
            commit_candidate="def456",
            branch_name="feature-branch",
        )
        serializer = DeterministicSerializer(config)

        file = ProcessedFile(
            status="M",
            path_old="test.py",
            path_new="test.py",
            rename_score=None,
            rename_tiebreaker=None,
            mode_old="100644",
            mode_new="100644",
            size_old=100,
            size_new=120,
            is_binary=False,
            is_submodule=False,
        )

        result = serializer.serialize_output(
            files=[file],
            omitted_files_count=0,
            notes=["test note"],
            git_version="2.34.1",
        )

        # Check structure
        assert "provenance" in result
        assert "files" in result
        assert "omitted_files_count" in result
        assert "notes" in result

        # Check provenance
        provenance = result["provenance"]
        assert provenance["repo_url"] == "https://example.com/repo.git"
        assert provenance["commit_good"] == "abc123"
        assert provenance["commit_candidate"] == "def456"
        assert provenance["branch_name"] == "feature-branch"
        assert provenance["git_version"] == "2.34.1"
        assert "checksum" in provenance

        # Check files
        assert len(result["files"]) == 1
        assert result["files"][0]["status"] == "M"

        # Check other fields
        assert result["omitted_files_count"] == 0
        assert result["notes"] == ["test note"]

    def test_checksum_computation(self):
        """Test checksum computation."""
        config = DiffConfig("repo", "good", "cand")
        serializer = DeterministicSerializer(config)

        payload = {
            "provenance": {
                "repo_url": "test",
                "commit_good": "abc",
                "commit_candidate": "def",
            },
            "files": [],
            "omitted_files_count": 0,
            "notes": [],
        }

        checksum = serializer._compute_checksum(payload)

        # Should be a valid SHA-256 hex string
        assert len(checksum) == 64
        assert all(c in "0123456789abcdef" for c in checksum)

    def test_deterministic_serialization(self):
        """Test that serialization is deterministic."""
        config = DiffConfig("repo", "good", "cand")
        serializer = DeterministicSerializer(config)

        payload = {
            "provenance": {
                "repo_url": "test",
                "commit_good": "abc",
                "commit_candidate": "def",
                "caps": {"total_bytes": 800000, "per_file_bytes": 64000},
            },
            "files": [
                {"status": "M", "path_new": "b.py"},
                {"status": "A", "path_new": "a.py"},
            ],
            "omitted_files_count": 0,
            "notes": ["note2", "note1"],
        }

        # Serialize twice
        json1 = serializer._to_deterministic_json_bytes(payload)
        json2 = serializer._to_deterministic_json_bytes(payload)

        # Should be identical
        assert json1 == json2

        # Parse and check ordering
        parsed = json.loads(json1.decode("utf-8"))
        assert parsed["files"][0]["path_new"] == "a.py"  # Should be sorted
        assert parsed["files"][1]["path_new"] == "b.py"
        assert parsed["notes"] == ["note1", "note2"]  # Should be sorted

    def test_success_envelope(self):
        """Test success envelope creation."""
        config = DiffConfig("repo", "good", "cand")
        serializer = DeterministicSerializer(config)

        payload = {"test": "data"}
        envelope = serializer.create_success_envelope(payload)

        assert envelope["ok"] is True
        assert envelope["data"] == payload

    def test_error_envelope(self):
        """Test error envelope creation."""
        config = DiffConfig("repo", "good", "cand")
        serializer = DeterministicSerializer(config)

        envelope = serializer.create_error_envelope(
            "TEST_ERROR", "Test message", {"detail": "value"}
        )

        assert envelope["ok"] is False
        assert envelope["error"]["code"] == "TEST_ERROR"
        assert envelope["error"]["message"] == "Test message"
        assert envelope["error"]["details"] == {"detail": "value"}

    def test_error_envelope_no_details(self):
        """Test error envelope creation without details."""
        config = DiffConfig("repo", "good", "cand")
        serializer = DeterministicSerializer(config)

        envelope = serializer.create_error_envelope("TEST_ERROR", "Test message")

        assert envelope["ok"] is False
        assert envelope["error"]["code"] == "TEST_ERROR"
        assert envelope["error"]["message"] == "Test message"
        assert "details" not in envelope["error"]
