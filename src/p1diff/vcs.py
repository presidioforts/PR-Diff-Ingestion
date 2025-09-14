"""Version control system operations for P1 Diff tool."""

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .config import DiffConfig
from .errors import (
    CloneFailedError,
    CommitNotFoundError,
    GitVersionUnsupportedError,
    NetworkTimeoutError,
)


@dataclass
class FileChange:
    """Represents a file change between two commits."""

    status: str  # A, M, D, R, C, T
    path_old: Optional[str]
    path_new: Optional[str]
    rename_score: Optional[int]
    rename_tiebreaker: Optional[str]
    mode_old: Optional[str]
    mode_new: Optional[str]
    size_old: Optional[int]
    size_new: Optional[int]
    is_binary: bool
    is_submodule: bool
    submodule_old_sha: Optional[str] = None
    submodule_new_sha: Optional[str] = None


class GitRepository:
    """Git repository operations."""

    def __init__(self, config: DiffConfig):
        """Initialize with configuration."""
        self.config = config
        self.workdir: Optional[Path] = None
        self._git_version: Optional[str] = None

    def __enter__(self) -> "GitRepository":
        """Context manager entry."""
        self.workdir = Path(tempfile.mkdtemp(prefix="p1diff_"))
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit with cleanup."""
        if self.workdir and self.workdir.exists():
            if not self.config.keep_workdir and not (
                exc_type and self.config.keep_on_error
            ):
                shutil.rmtree(self.workdir, ignore_errors=True)

    def _run_git(
        self,
        args: List[str],
        timeout: int = 300,
        check: bool = True,
        capture_output: bool = True,
    ) -> subprocess.CompletedProcess:
        """Run git command with proper environment and error handling."""
        # Enforce deterministic git behavior across platforms
        cmd = [
            "git",
            "-c",
            "core.autocrlf=false",
            "-c",
            "color.ui=false",
        ] + args
        try:
            result = subprocess.run(
                cmd,
                cwd=self.workdir,
                env=self.config.git_env,
                timeout=timeout,
                check=check,
                capture_output=capture_output,
                text=True,
            )
            return result
        except subprocess.TimeoutExpired as e:
            raise NetworkTimeoutError("git operation", timeout) from e
        except subprocess.CalledProcessError as e:
            if "clone" in args[0]:
                raise CloneFailedError(self.config.repo_url, e.stderr or str(e)) from e
            raise

    def validate_git_version(self) -> str:
        """Validate Git version meets minimum requirements."""
        if self._git_version:
            return self._git_version

        try:
            result = subprocess.run(
                ["git", "--version"],
                capture_output=True,
                text=True,
                check=True,
                timeout=10,
            )
            version_line = result.stdout.strip()
            # Extract version number from "git version 2.34.1"
            match = re.search(r"git version (\d+\.\d+(?:\.\d+)?)", version_line)
            if not match:
                raise GitVersionUnsupportedError("unknown", "2.30")

            version_str = match.group(1)
            version_parts = [int(x) for x in version_str.split(".")]

            # Check if version >= 2.30
            if version_parts[0] < 2 or (version_parts[0] == 2 and version_parts[1] < 30):
                raise GitVersionUnsupportedError(version_str, "2.30")

            self._git_version = version_str
            return version_str

        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
            raise GitVersionUnsupportedError("unavailable", "2.30") from e

    def clone_and_setup(self) -> None:
        """Clone repository and set up workspace."""
        if not self.workdir:
            raise RuntimeError("Workdir not initialized")

        # Validate git version first
        self.validate_git_version()

        # Clone repository with minimal depth
        clone_args = [
            "clone",
            "--no-checkout",
            "--filter=blob:none",
            self.config.repo_url,
            ".",  # clone into the already-created empty workdir
        ]

        if self.config.branch_name:
            clone_args.extend(["--branch", self.config.branch_name])

        try:
            # Run clone within the empty workdir so target "." is valid
            result = subprocess.run(
                [
                    "git",
                    "-c",
                    "core.autocrlf=false",
                    "-c",
                    "color.ui=false",
                ]
                + clone_args,
                cwd=self.workdir,
                env=self.config.git_env,
                timeout=300,
                check=True,
                capture_output=True,
                text=True,
            )
        except Exception as e:
            raise CloneFailedError(self.config.repo_url, str(e)) from e

        # Fetch specific commits if they're not already available
        self._ensure_commits_available()

    def _ensure_commits_available(self) -> None:
        """Ensure both commits are available in the repository."""
        missing_commits = []

        for commit_name, commit_sha in [
            ("good", self.config.commit_good),
            ("candidate", self.config.commit_candidate),
        ]:
            try:
                self._run_git(["cat-file", "-e", commit_sha])
            except subprocess.CalledProcessError:
                missing_commits.append(commit_sha)

        if missing_commits:
            # Try to fetch missing commits
            try:
                self._run_git(["fetch", "origin"] + missing_commits, timeout=300)
                # Verify again
                still_missing = []
                for commit_sha in missing_commits:
                    try:
                        self._run_git(["cat-file", "-e", commit_sha])
                    except subprocess.CalledProcessError:
                        still_missing.append(commit_sha)
                if still_missing:
                    raise CommitNotFoundError(still_missing, self.config.repo_url)
            except subprocess.CalledProcessError:
                raise CommitNotFoundError(missing_commits, self.config.repo_url)

    def get_file_changes(self) -> List[FileChange]:
        """Get list of file changes between commits with rename detection."""
        # Use git diff with rename detection
        diff_args = [
            "diff",
            "--name-status",
            "--find-renames=" + str(self.config.find_renames_threshold),
            "--no-color",
            f"{self.config.commit_good}..{self.config.commit_candidate}",
        ]

        result = self._run_git(diff_args)
        changes = []

        for line in result.stdout.strip().split("\n"):
            if not line:
                continue

            change = self._parse_diff_line(line)
            if change:
                changes.append(change)

        # Sort changes deterministically
        changes.sort(key=self._change_sort_key)

        # Resolve rename ties deterministically
        self._resolve_rename_ties(changes)

        return changes

    def _parse_diff_line(self, line: str) -> Optional[FileChange]:
        """Parse a single line from git diff --name-status output."""
        parts = line.split("\t")
        if len(parts) < 2:
            return None

        status_part = parts[0]
        status = status_part[0]

        # Handle rename/copy with score
        rename_score = None
        if status in "RC" and len(status_part) > 1:
            score_match = re.search(r"(\d+)", status_part)
            if score_match:
                rename_score = int(score_match.group(1))

        # Extract paths
        if status in "RC":
            # Rename/copy: old_path -> new_path
            if len(parts) >= 3:
                path_old, path_new = parts[1], parts[2]
            else:
                return None
        elif status == "D":
            # Delete: only old path
            path_old, path_new = parts[1], None
        else:
            # Add/Modify: only new path
            path_old, path_new = None, parts[1]

        # Get file metadata
        mode_old, mode_new, size_old, size_new = self._get_file_metadata(
            path_old, path_new
        )

        # Check if binary or submodule
        is_binary, is_submodule = self._check_file_type(path_old, path_new)

        # Get submodule SHAs if applicable
        submodule_old_sha, submodule_new_sha = None, None
        if is_submodule:
            submodule_old_sha, submodule_new_sha = self._get_submodule_shas(
                path_old, path_new
            )

        return FileChange(
            status=status,
            path_old=path_old,
            path_new=path_new,
            rename_score=rename_score,
            rename_tiebreaker=None,  # Will be set later if needed
            mode_old=mode_old,
            mode_new=mode_new,
            size_old=size_old,
            size_new=size_new,
            is_binary=is_binary,
            is_submodule=is_submodule,
            submodule_old_sha=submodule_old_sha,
            submodule_new_sha=submodule_new_sha,
        )

    def _get_file_metadata(
        self, path_old: Optional[str], path_new: Optional[str]
    ) -> Tuple[Optional[str], Optional[str], Optional[int], Optional[int]]:
        """Get file mode and size metadata."""
        mode_old, mode_new = None, None
        size_old, size_new = None, None

        # Get old file metadata
        if path_old:
            try:
                result = self._run_git([
                    "ls-tree",
                    "-l",
                    self.config.commit_good,
                    path_old,
                ])
                output = result.stdout.strip()
                if output:
                    # Expected: "<mode> <type> <object> <size>\t<path>" (size only for blobs)
                    meta_and_path = output.split("\t", 1)
                    meta_parts = meta_and_path[0].split()
                    if len(meta_parts) >= 3:
                        mode_old = meta_parts[0]
                        if len(meta_parts) >= 4 and meta_parts[1] != "commit":
                            try:
                                size_old = int(meta_parts[3])
                            except ValueError:
                                size_old = None
            except subprocess.CalledProcessError:
                pass

        # Get new file metadata
        if path_new:
            try:
                result = self._run_git([
                    "ls-tree",
                    "-l",
                    self.config.commit_candidate,
                    path_new,
                ])
                output = result.stdout.strip()
                if output:
                    meta_and_path = output.split("\t", 1)
                    meta_parts = meta_and_path[0].split()
                    if len(meta_parts) >= 3:
                        mode_new = meta_parts[0]
                        if len(meta_parts) >= 4 and meta_parts[1] != "commit":
                            try:
                                size_new = int(meta_parts[3])
                            except ValueError:
                                size_new = None
            except subprocess.CalledProcessError:
                pass

        return mode_old, mode_new, size_old, size_new

    def _check_file_type(
        self, path_old: Optional[str], path_new: Optional[str]
    ) -> Tuple[bool, bool]:
        """Check if file is binary or submodule."""
        is_binary = False
        is_submodule = False

        # Check the new file (or old if deleted)
        check_path = path_new or path_old
        if not check_path:
            return False, False

        commit = (
            self.config.commit_candidate
            if path_new
            else self.config.commit_good
        )

        try:
            # Check if it's a submodule (gitlink)
            result = self._run_git(["ls-tree", commit, check_path])
            if result.stdout.strip():
                parts = result.stdout.strip().split()
                if len(parts) >= 2 and parts[1] == "commit":
                    is_submodule = True
                    return is_binary, is_submodule

            # Check if binary using git's detection (single invocation)
            try:
                result = self._run_git([
                    "diff",
                    "--numstat",
                    f"{self.config.commit_good}..{self.config.commit_candidate}",
                    "--",
                    check_path,
                ])
                if result.stdout.strip():
                    first = result.stdout.strip().split("\n")[0]
                    # Binary shows as "-\t-\t<path>"
                    if first.startswith("-\t-\t"):
                        is_binary = True
            except subprocess.CalledProcessError:
                pass

        except subprocess.CalledProcessError:
            pass

        return is_binary, is_submodule

    def _get_submodule_shas(
        self, path_old: Optional[str], path_new: Optional[str]
    ) -> Tuple[Optional[str], Optional[str]]:
        """Get submodule SHA values."""
        old_sha, new_sha = None, None

        if path_old:
            try:
                result = self._run_git([
                    "ls-tree",
                    self.config.commit_good,
                    path_old,
                ])
                if result.stdout.strip():
                    parts = result.stdout.strip().split()
                    if len(parts) >= 3:
                        old_sha = parts[2]
            except subprocess.CalledProcessError:
                pass

        if path_new:
            try:
                result = self._run_git([
                    "ls-tree",
                    self.config.commit_candidate,
                    path_new,
                ])
                if result.stdout.strip():
                    parts = result.stdout.strip().split()
                    if len(parts) >= 3:
                        new_sha = parts[2]
            except subprocess.CalledProcessError:
                pass

        return old_sha, new_sha

    def _change_sort_key(self, change: FileChange) -> Tuple[str, str]:
        """Generate sort key for deterministic ordering."""
        # Sort by effective new path (fallback to old), then by status
        effective_path = change.path_new or change.path_old or ""
        return (effective_path, change.status)

    def _resolve_rename_ties(self, changes: List[FileChange]) -> None:
        """Resolve rename ties deterministically."""
        # Group renames by score and paths to find ties
        rename_groups: Dict[Tuple[int, str, str], List[FileChange]] = {}

        for change in changes:
            if change.status in "RC" and change.rename_score is not None:
                key = (
                    change.rename_score,
                    change.path_old or "",
                    change.path_new or "",
                )
                if key not in rename_groups:
                    rename_groups[key] = []
                rename_groups[key].append(change)

        # For groups with multiple entries, apply tie-breaking
        for group in rename_groups.values():
            if len(group) > 1:
                # Sort by: path similarity -> size delta -> lexicographic old path
                group.sort(key=lambda c: (
                    self._path_similarity(c.path_old or "", c.path_new or ""),
                    abs((c.size_new or 0) - (c.size_old or 0)),
                    c.path_old or "",
                ))

                # Set tiebreaker for all but the first (winner)
                for i, change in enumerate(group):
                    if i == 0:
                        change.rename_tiebreaker = "path"
                    else:
                        change.rename_tiebreaker = "lex"

    def _path_similarity(self, path1: str, path2: str) -> float:
        """Calculate path similarity for tie-breaking."""
        if not path1 or not path2:
            return 0.0

        # Simple similarity based on common path components
        parts1 = Path(path1).parts
        parts2 = Path(path2).parts

        common = 0
        for p1, p2 in zip(parts1, parts2):
            if p1 == p2:
                common += 1
            else:
                break

        total = max(len(parts1), len(parts2))
        return common / total if total > 0 else 0.0

    def get_unified_diff(self, change: FileChange) -> str:
        """Get unified diff for a file change."""
        if change.is_binary or change.is_submodule:
            return ""

        diff_args = [
            "diff",
            f"--unified={self.config.context_lines}",
            "--no-color",
            "--no-prefix",
            f"{self.config.commit_good}..{self.config.commit_candidate}",
            "--",
        ]

        # Add the appropriate path
        if change.path_new:
            diff_args.append(change.path_new)
        elif change.path_old:
            diff_args.append(change.path_old)
        else:
            return ""

        try:
            result = self._run_git(diff_args, check=False)
            return result.stdout
        except subprocess.CalledProcessError:
            return ""
