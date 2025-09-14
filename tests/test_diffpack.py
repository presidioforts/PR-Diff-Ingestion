"""Tests for diff processing module."""

import pytest

from p1diff.diffpack import DiffProcessor, DiffHunk, ProcessedFile
from p1diff.vcs import FileChange


class TestDiffProcessor:
    """Test DiffProcessor class."""

    def test_process_file_change_basic(self):
        """Test basic file change processing."""
        change = FileChange(
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

        processor = DiffProcessor()
        result = processor.process_file_change(change, "")

        assert result.status == "M"
        assert result.path_old == "test.py"
        assert result.path_new == "test.py"
        assert result.mode_old == "100644"
        assert result.mode_new == "100644"
        assert result.size_old == 100
        assert result.size_new == 120
        assert result.is_binary is False
        assert result.is_submodule is False
        assert result.hunks == []

    def test_process_file_change_binary(self):
        """Test binary file processing."""
        change = FileChange(
            status="M",
            path_old="image.png",
            path_new="image.png",
            rename_score=None,
            rename_tiebreaker=None,
            mode_old="100644",
            mode_new="100644",
            size_old=1000,
            size_new=1200,
            is_binary=True,
            is_submodule=False,
        )

        processor = DiffProcessor()
        result = processor.process_file_change(change, "some diff content")

        assert result.is_binary is True
        assert result.hunks == []  # No hunks for binary files

    def test_process_file_change_submodule(self):
        """Test submodule processing."""
        change = FileChange(
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
            submodule_old_sha="abc123",
            submodule_new_sha="def456",
        )

        processor = DiffProcessor()
        result = processor.process_file_change(change, "")

        assert result.is_submodule is True
        assert result.submodule == {"old_sha": "abc123", "new_sha": "def456"}
        assert result.hunks == []  # No hunks for submodules

    def test_process_file_change_rename(self):
        """Test rename processing."""
        change = FileChange(
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

        processor = DiffProcessor()
        result = processor.process_file_change(change, "")

        assert result.status == "R"
        assert result.path_old == "old_name.py"
        assert result.path_new == "new_name.py"
        assert result.rename_score == 95
        assert result.rename_tiebreaker == "path"

    def test_split_into_hunks_single(self):
        """Test splitting diff into single hunk."""
        unified_diff = """@@ -1,3 +1,4 @@
 line1
-line2
+line2 modified
+new line
 line3"""

        processor = DiffProcessor()
        hunks = processor._split_into_hunks(unified_diff)

        assert len(hunks) == 1
        hunk = hunks[0]
        assert hunk.header == "@@ -1,3 +1,4 @@"
        assert hunk.old_start == 1
        assert hunk.old_lines == 3
        assert hunk.new_start == 1
        assert hunk.new_lines == 4
        assert hunk.added == 2
        assert hunk.deleted == 1

    def test_split_into_hunks_multiple(self):
        """Test splitting diff into multiple hunks."""
        unified_diff = """@@ -1,3 +1,3 @@
 line1
-old line2
+new line2
 line3
@@ -10,2 +10,3 @@
 line10
+added line
 line11"""

        processor = DiffProcessor()
        hunks = processor._split_into_hunks(unified_diff)

        assert len(hunks) == 2

        # First hunk
        hunk1 = hunks[0]
        assert hunk1.header == "@@ -1,3 +1,3 @@"
        assert hunk1.old_start == 1
        assert hunk1.old_lines == 3
        assert hunk1.new_start == 1
        assert hunk1.new_lines == 3
        assert hunk1.added == 1
        assert hunk1.deleted == 1

        # Second hunk
        hunk2 = hunks[1]
        assert hunk2.header == "@@ -10,2 +10,3 @@"
        assert hunk2.old_start == 10
        assert hunk2.old_lines == 2
        assert hunk2.new_start == 10
        assert hunk2.new_lines == 3
        assert hunk2.added == 1
        assert hunk2.deleted == 0

    def test_detect_eol_only_change(self):
        """Test EOL-only change detection."""
        # EOL change: CRLF to LF
        eol_diff = """@@ -1,1 +1,1 @@
-line with CRLF\r
+line with LF"""

        processor = DiffProcessor()
        is_eol_only = processor._detect_eol_only_change(eol_diff)
        assert is_eol_only is True

        # Not EOL-only change
        content_diff = """@@ -1,1 +1,1 @@
-old content
+new content"""

        is_eol_only = processor._detect_eol_only_change(content_diff)
        assert is_eol_only is False

    def test_detect_whitespace_only_change(self):
        """Test whitespace-only change detection."""
        # Whitespace-only change
        ws_diff = """@@ -1,2 +1,2 @@
-def function():
-    return True
+def  function( ):
+     return True"""

        processor = DiffProcessor()
        is_ws_only = processor._detect_whitespace_only_change(ws_diff)
        assert is_ws_only is True

        # Not whitespace-only change
        content_diff = """@@ -1,1 +1,1 @@
-def old_function():
+def new_function():"""

        is_ws_only = processor._detect_whitespace_only_change(content_diff)
        assert is_ws_only is False

    def test_create_hunk_with_context(self):
        """Test hunk creation with context lines."""
        header = "@@ -5,7 +5,8 @@"
        header_match = processor = DiffProcessor()
        match = processor.hunk_header_pattern.match(header)
        
        lines = [
            " context1",
            " context2", 
            "-removed line",
            "+added line1",
            "+added line2",
            " context3",
            " context4"
        ]

        hunk = processor._create_hunk(header, match, lines)

        assert hunk.header == "@@ -5,7 +5,8 @@"
        assert hunk.old_start == 5
        assert hunk.old_lines == 7
        assert hunk.new_start == 5
        assert hunk.new_lines == 8
        assert hunk.added == 2
        assert hunk.deleted == 1
        assert "context1" in hunk.patch
        assert "removed line" in hunk.patch
        assert "added line1" in hunk.patch
