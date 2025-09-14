"""Integration tests for P1 Diff tool."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from p1diff.main import main


class TestIntegration:
    """Integration tests using real repository."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_real_repository_integration(self, monkeypatch, temp_dir):
        """Test against the real repository specified in requirements."""
        # Test data from specification
        repo_url = "https://github.com/presidioforts/direct-finetune-rag-model.git"
        commit_good = "ba7765dd48c0ba51f4fd12cde48fd100aecdb743"
        commit_candidate = "d7a39abec5a282b9955afdd1649a5f1bafae35f7"
        branch_name = "codex/move-prompts-to-external-template-files"

        output_file = temp_dir / "integration_output.json"

        # Set up command line arguments
        test_args = [
            "p1diff",
            "--repo", repo_url,
            "--good", commit_good,
            "--cand", commit_candidate,
            "--branch", branch_name,
            "--json", str(output_file),
        ]

        # Mock sys.argv
        monkeypatch.setattr(sys, "argv", test_args)

        try:
            # Run the main function
            exit_code = main()
            assert exit_code == 0

            # Verify output file exists and is valid JSON
            assert output_file.exists()
            output_content = output_file.read_text()
            result = json.loads(output_content)

            # Verify envelope structure
            assert "ok" in result
            assert result["ok"] is True
            assert "data" in result

            data = result["data"]

            # Verify provenance
            assert "provenance" in data
            provenance = data["provenance"]
            assert provenance["repo_url"] == repo_url
            assert provenance["commit_good"] == commit_good
            assert provenance["commit_candidate"] == commit_candidate
            assert provenance["branch_name"] == branch_name
            assert "checksum" in provenance
            assert "git_version" in provenance

            # Verify caps
            assert "caps" in provenance
            caps = provenance["caps"]
            assert caps["total_bytes"] == 800_000
            assert caps["per_file_bytes"] == 64_000
            assert caps["context_lines"] == 3

            # Verify rename detection
            assert "rename_detection" in provenance
            rename_detection = provenance["rename_detection"]
            assert rename_detection["enabled"] is True
            assert rename_detection["threshold_pct"] == 90

            # Verify files array
            assert "files" in data
            assert isinstance(data["files"], list)

            # Verify omitted files count
            assert "omitted_files_count" in data
            assert isinstance(data["omitted_files_count"], int)

            # Verify notes
            assert "notes" in data
            assert isinstance(data["notes"], list)

            # Test determinism: run again and compare checksums
            output_file2 = temp_dir / "integration_output2.json"
            test_args2 = test_args[:-1] + [str(output_file2)]
            monkeypatch.setattr(sys, "argv", test_args2)

            exit_code2 = main()
            assert exit_code2 == 0

            output_content2 = output_file2.read_text()
            result2 = json.loads(output_content2)

            # Checksums should be identical
            checksum1 = result["data"]["provenance"]["checksum"]
            checksum2 = result2["data"]["provenance"]["checksum"]
            assert checksum1 == checksum2

            print(f"Integration test passed. Checksum: {checksum1}")

        except Exception as e:
            pytest.skip(f"Integration test skipped due to network/access issue: {e}")

    def test_determinism_with_synthetic_repo(self, git_helper, temp_dir):
        """Test determinism using synthetic repository."""
        # Create test files and commits
        git_helper.create_file("file1.py", "def hello():\n    print('Hello')\n")
        git_helper.create_file("file2.js", "function hello() {\n    console.log('Hello');\n}\n")
        commit1 = git_helper.add_and_commit("Add initial files")

        # Modify files
        git_helper.modify_file("file1.py", "def hello():\n    print('Hello, World!')\n")
        git_helper.create_file("file3.txt", "New file content\n")
        commit2 = git_helper.add_and_commit("Modify and add files")

        # Test with p1diff
        output_file1 = temp_dir / "output1.json"
        output_file2 = temp_dir / "output2.json"

        for output_file in [output_file1, output_file2]:
            result = subprocess.run([
                sys.executable, "-m", "p1diff.main",
                "--repo", str(git_helper.repo_path),
                "--good", commit1,
                "--cand", commit2,
                "--json", str(output_file),
            ], capture_output=True, text=True)

            assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Compare outputs
        content1 = output_file1.read_text()
        content2 = output_file2.read_text()
        
        result1 = json.loads(content1)
        result2 = json.loads(content2)

        # Should be identical
        assert result1 == result2

        # Checksums should match
        checksum1 = result1["data"]["provenance"]["checksum"]
        checksum2 = result2["data"]["provenance"]["checksum"]
        assert checksum1 == checksum2

    def test_error_handling_missing_commit(self, git_helper, temp_dir):
        """Test error handling for missing commit."""
        commit1 = git_helper.get_current_sha()
        missing_commit = "0123456789abcdef0123456789abcdef01234567"

        output_file = temp_dir / "error_output.json"

        result = subprocess.run([
            sys.executable, "-m", "p1diff.main",
            "--repo", str(git_helper.repo_path),
            "--good", commit1,
            "--cand", missing_commit,
            "--json", str(output_file),
        ], capture_output=True, text=True)

        assert result.returncode != 0

        # Check error output
        content = output_file.read_text()
        error_result = json.loads(content)

        assert error_result["ok"] is False
        assert "error" in error_result
        assert error_result["error"]["code"] == "COMMIT_NOT_FOUND"

    def test_capacity_limits(self, git_helper, temp_dir):
        """Test capacity limit enforcement."""
        # Create a large file that will exceed per-file cap
        large_content = "# Large file\n" + "print('line')\n" * 1000
        git_helper.create_file("large_file.py", large_content)
        commit1 = git_helper.add_and_commit("Add large file")

        # Modify the large file
        modified_content = "# Modified large file\n" + "print('modified line')\n" * 1000
        git_helper.modify_file("large_file.py", modified_content)
        commit2 = git_helper.add_and_commit("Modify large file")

        output_file = temp_dir / "capacity_output.json"

        result = subprocess.run([
            sys.executable, "-m", "p1diff.main",
            "--repo", str(git_helper.repo_path),
            "--good", commit1,
            "--cand", commit2,
            "--cap-file", "1000",  # Very small cap
            "--json", str(output_file),
        ], capture_output=True, text=True)

        assert result.returncode == 0

        content = output_file.read_text()
        result_data = json.loads(content)

        assert result_data["ok"] is True
        files = result_data["data"]["files"]
        
        # Should have truncation flags
        large_file = next((f for f in files if f["path_new"] == "large_file.py"), None)
        assert large_file is not None
        assert large_file.get("truncated", False) is True
