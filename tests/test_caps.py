"""Tests for capacity management module."""

import pytest

from p1diff.caps import CapacityManager
from p1diff.config import DiffConfig
from p1diff.diffpack import DiffHunk, ProcessedFile


class TestCapacityManager:
    """Test CapacityManager class."""

    def test_calculate_file_size_empty(self):
        """Test file size calculation for empty file."""
        config = DiffConfig("repo", "good", "cand")
        manager = CapacityManager(config)

        file = ProcessedFile(
            status="A",
            path_old=None,
            path_new="test.py",
            rename_score=None,
            rename_tiebreaker=None,
            mode_old=None,
            mode_new="100644",
            size_old=None,
            size_new=100,
            is_binary=False,
            is_submodule=False,
            hunks=[],
        )

        size = manager._calculate_file_size(file)
        assert size == 0

    def test_calculate_file_size_with_hunks(self):
        """Test file size calculation with hunks."""
        config = DiffConfig("repo", "good", "cand")
        manager = CapacityManager(config)

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
            size_new=100,
            is_binary=False,
            is_submodule=False,
            hunks=[hunk1, hunk2],
        )

        size = manager._calculate_file_size(file)
        expected_size = len(hunk1.patch.encode("utf-8")) + len(hunk2.patch.encode("utf-8"))
        assert size == expected_size

    def test_apply_caps_no_limits_exceeded(self):
        """Test applying caps when no limits are exceeded."""
        config = DiffConfig("repo", "good", "cand", cap_total=1000, cap_file=500)
        manager = CapacityManager(config)

        hunk = DiffHunk(
            header="@@ -1,1 +1,1 @@",
            old_start=1,
            old_lines=1,
            new_start=1,
            new_lines=1,
            added=1,
            deleted=1,
            patch="@@ -1,1 +1,1 @@\n-old\n+new",  # Small patch
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
            size_new=100,
            is_binary=False,
            is_submodule=False,
            hunks=[hunk],
        )

        processed_files, omitted_count = manager.apply_caps([file])

        assert len(processed_files) == 1
        assert omitted_count == 0
        assert processed_files[0].truncated is False
        assert processed_files[0].summarized is False
        assert len(processed_files[0].hunks) == 1

    def test_apply_caps_global_limit_exceeded(self):
        """Test applying caps when global limit is exceeded."""
        config = DiffConfig("repo", "good", "cand", cap_total=50, cap_file=100)
        manager = CapacityManager(config)

        # Create a hunk that's larger than global cap
        large_patch = "@@ -1,1 +1,1 @@\n" + "-old line\n+new line\n" * 10
        hunk = DiffHunk(
            header="@@ -1,1 +1,1 @@",
            old_start=1,
            old_lines=1,
            new_start=1,
            new_lines=1,
            added=1,
            deleted=1,
            patch=large_patch,
        )

        file1 = ProcessedFile(
            status="M",
            path_old="test1.py",
            path_new="test1.py",
            rename_score=None,
            rename_tiebreaker=None,
            mode_old="100644",
            mode_new="100644",
            size_old=100,
            size_new=100,
            is_binary=False,
            is_submodule=False,
            hunks=[hunk],
        )

        file2 = ProcessedFile(
            status="M",
            path_old="test2.py",
            path_new="test2.py",
            rename_score=None,
            rename_tiebreaker=None,
            mode_old="100644",
            mode_new="100644",
            size_old=100,
            size_new=100,
            is_binary=False,
            is_submodule=False,
            hunks=[hunk],
        )

        processed_files, omitted_count = manager.apply_caps([file1, file2])

        assert len(processed_files) == 2
        assert omitted_count == 1  # Second file should be omitted
        assert len(processed_files[0].hunks) > 0  # First file should have hunks
        assert len(processed_files[1].hunks) == 0  # Second file should have no hunks

    def test_apply_caps_per_file_limit_exceeded(self):
        """Test applying caps when per-file limit is exceeded."""
        config = DiffConfig("repo", "good", "cand", cap_total=1000, cap_file=50)
        manager = CapacityManager(config)

        # Create multiple hunks that together exceed per-file cap
        hunks = []
        for i in range(5):
            patch = f"@@ -{i+1},1 +{i+1},1 @@\n-old line {i}\n+new line {i}\n"
            hunk = DiffHunk(
                header=f"@@ -{i+1},1 +{i+1},1 @@",
                old_start=i+1,
                old_lines=1,
                new_start=i+1,
                new_lines=1,
                added=1,
                deleted=1,
                patch=patch,
            )
            hunks.append(hunk)

        file = ProcessedFile(
            status="M",
            path_old="test.py",
            path_new="test.py",
            rename_score=None,
            rename_tiebreaker=None,
            mode_old="100644",
            mode_new="100644",
            size_old=100,
            size_new=100,
            is_binary=False,
            is_submodule=False,
            hunks=hunks,
        )

        processed_files, omitted_count = manager.apply_caps([file])

        assert len(processed_files) == 1
        assert omitted_count == 0
        processed_file = processed_files[0]
        
        # File should be truncated
        assert processed_file.truncated is True
        assert processed_file.omitted_hunks_count is not None
        assert processed_file.omitted_hunks_count > 0
        assert len(processed_file.hunks) < len(hunks)  # Some hunks should be removed

    def test_apply_caps_lockfile_summarized(self):
        """Test that lockfiles are summarized when oversized."""
        config = DiffConfig("repo", "good", "cand", cap_total=1000, cap_file=50)
        manager = CapacityManager(config)

        # Create a large hunk for a lockfile
        large_patch = "@@ -1,1 +1,1 @@\n" + "-old line\n+new line\n" * 20
        hunk = DiffHunk(
            header="@@ -1,1 +1,1 @@",
            old_start=1,
            old_lines=1,
            new_start=1,
            new_lines=1,
            added=1,
            deleted=1,
            patch=large_patch,
        )

        lockfile = ProcessedFile(
            status="M",
            path_old="package-lock.json",
            path_new="package-lock.json",
            rename_score=None,
            rename_tiebreaker=None,
            mode_old="100644",
            mode_new="100644",
            size_old=1000,
            size_new=1200,
            is_binary=False,
            is_submodule=False,
            hunks=[hunk],
        )

        processed_files, omitted_count = manager.apply_caps([lockfile])

        assert len(processed_files) == 1
        assert omitted_count == 0
        processed_file = processed_files[0]
        
        # Lockfile should be summarized, not truncated
        assert processed_file.summarized is True
        assert processed_file.truncated is False
        assert len(processed_file.hunks) == 0  # Hunks should be removed

    def test_truncate_hunk_context(self):
        """Test hunk context truncation."""
        config = DiffConfig("repo", "good", "cand")
        manager = CapacityManager(config)

        # Create a hunk with lots of context
        patch_lines = [
            "@@ -5,10 +5,10 @@",
            " context1",
            " context2",
            " context3",
            "-old line",
            "+new line",
            " context4",
            " context5",
            " context6",
        ]
        patch = "\n".join(patch_lines)

        hunk = DiffHunk(
            header="@@ -5,10 +5,10 @@",
            old_start=5,
            old_lines=10,
            new_start=5,
            new_lines=10,
            added=1,
            deleted=1,
            patch=patch,
        )

        # Try to truncate to a very small size
        truncated_hunk = manager._truncate_hunk_context(hunk, 100)

        if truncated_hunk:
            # Should have reduced context
            assert len(truncated_hunk.patch) < len(patch)
            assert "-old line" in truncated_hunk.patch
            assert "+new line" in truncated_hunk.patch
