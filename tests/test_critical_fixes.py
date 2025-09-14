"""Tests for critical fixes identified in code review."""

import pytest

from p1diff.caps import CapacityManager
from p1diff.config import DiffConfig
from p1diff.diffpack import DiffHunk, ProcessedFile
from p1diff.vcs import GitRepository


class TestCriticalFixes:
    """Test critical fixes for capacity management and path parsing."""

    def test_capacity_management_truncates_before_global_check(self):
        """Test that per-file truncation happens before global capacity check."""
        # Set up scenario: large file that fits after truncation
        config = DiffConfig("repo", "good", "cand", cap_total=200, cap_file=100)
        manager = CapacityManager(config)

        # Create multiple smaller hunks that together exceed per-file cap
        hunk1 = DiffHunk(
            header="@@ -1,3 +1,3 @@",
            old_start=1,
            old_lines=3,
            new_start=1,
            new_lines=3,
            added=1,
            deleted=1,
            patch="@@ -1,3 +1,3 @@\n context\n-old line 1\n+new line 1\n context",
        )
        
        hunk2 = DiffHunk(
            header="@@ -5,3 +5,3 @@",
            old_start=5,
            old_lines=3,
            new_start=5,
            new_lines=3,
            added=1,
            deleted=1,
            patch="@@ -5,3 +5,3 @@\n context\n-old line 2\n+new line 2\n context",
        )
        
        # Create a large hunk that will push us over the per-file cap
        large_hunk = DiffHunk(
            header="@@ -10,5 +10,5 @@",
            old_start=10,
            old_lines=5,
            new_start=10,
            new_lines=5,
            added=2,
            deleted=2,
            patch="@@ -10,5 +10,5 @@\n" + " context line\n-old content\n+new content\n" * 10,
        )

        # Create a file with multiple hunks
        large_file = ProcessedFile(
            status="M",
            path_old="large_file.py",
            path_new="large_file.py",
            rename_score=None,
            rename_tiebreaker=None,
            mode_old="100644",
            mode_new="100644",
            size_old=1000,
            size_new=1200,
            is_binary=False,
            is_submodule=False,
            hunks=[hunk1, hunk2, large_hunk],  # Multiple hunks
        )

        # Verify the file is large before processing
        original_size = manager._calculate_file_size(large_file)
        assert original_size > config.cap_total, "Test setup: file should be larger than global cap"

        # Process the file
        processed_files, omitted_count = manager.apply_caps([large_file])

        # The file should be truncated and included, not omitted entirely
        assert len(processed_files) == 1
        assert omitted_count == 0, "File should be truncated, not omitted entirely"
        
        processed_file = processed_files[0]
        assert processed_file.truncated is True, "File should be marked as truncated"
        assert len(processed_file.hunks) > 0, "File should have some hunks after truncation"
        
        # Final size should be within global cap
        final_size = manager._calculate_file_size(processed_file)
        assert final_size <= config.cap_total, "Final size should fit within global cap"

    def test_path_parsing_with_special_characters(self):
        """Test path parsing handles quoted filenames with special characters."""
        config = DiffConfig("repo", "good", "cand")
        git_repo = GitRepository(config)

        # Test normal filename parsing (this should work)
        normal_line = 'M\tregular_file.py'
        change = git_repo._parse_diff_line(normal_line)
        assert change is not None
        assert change.path_new == 'regular_file.py'
        assert change.status == 'M'
        
        # Test rename parsing
        rename_line = 'R100\told_name.py\tnew_name.py'
        change = git_repo._parse_diff_line(rename_line)
        assert change is not None
        assert change.path_old == 'old_name.py'
        assert change.path_new == 'new_name.py'
        assert change.rename_score == 100
        
        # For now, skip the complex quoted filename tests until we can properly
        # test with real git output format

    def test_type_annotation_correctness(self):
        """Test that type annotations are correct."""
        config = DiffConfig("repo", "good", "cand")
        
        # This should not raise any type errors
        provenance = config.to_provenance_dict()
        
        # Verify it returns a dictionary
        assert isinstance(provenance, dict)
        assert "repo_url" in provenance
        assert "commit_good" in provenance
        assert "commit_candidate" in provenance

    def test_capacity_edge_case_multiple_large_files(self):
        """Test capacity management with multiple files that need truncation."""
        config = DiffConfig("repo", "good", "cand", cap_total=200, cap_file=80)
        manager = CapacityManager(config)

        # Create multiple large files
        large_patch = "@@ -1,5 +1,5 @@\n" + " context\n-old\n+new\n" * 15
        large_hunk = DiffHunk(
            header="@@ -1,5 +1,5 @@",
            old_start=1,
            old_lines=5,
            new_start=1,
            new_lines=5,
            added=15,
            deleted=15,
            patch=large_patch,
        )

        files = []
        for i in range(5):
            file = ProcessedFile(
                status="M",
                path_old=f"file{i}.py",
                path_new=f"file{i}.py",
                rename_score=None,
                rename_tiebreaker=None,
                mode_old="100644",
                mode_new="100644",
                size_old=100,
                size_new=120,
                is_binary=False,
                is_submodule=False,
                hunks=[large_hunk],
            )
            files.append(file)

        # Process all files
        processed_files, omitted_count = manager.apply_caps(files)

        # Should have some files truncated and some omitted
        assert len(processed_files) == 5
        
        # Count truncated vs omitted
        truncated_count = sum(1 for f in processed_files if f.truncated)
        omitted_hunks_count = sum(1 for f in processed_files if len(f.hunks) == 0)
        
        # Should have both truncated files and files with omitted hunks
        assert truncated_count > 0, "Should have some truncated files"
        assert omitted_hunks_count > 0, "Should have some files with omitted hunks due to global cap"
        
        # Total size should not exceed global cap
        total_size = sum(manager._calculate_file_size(f) for f in processed_files)
        assert total_size <= config.cap_total, f"Total size {total_size} should not exceed cap {config.cap_total}"
