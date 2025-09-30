"""Diff processing and hunk splitting for P1 Diff tool."""

import logging
import re
from dataclasses import dataclass
from typing import List, Optional, Tuple

from .vcs import FileChange

logger = logging.getLogger(__name__)


@dataclass
class DiffHunk:
    """Represents a single diff hunk."""

    header: str
    old_start: int
    old_lines: int
    new_start: int
    new_lines: int
    added: int
    deleted: int
    patch: str


@dataclass
class ProcessedFile:
    """Represents a processed file with metadata and hunks."""

    # File metadata
    status: str
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

    # Change flags
    eol_only_change: bool = False
    whitespace_only_change: bool = False

    # Processing flags
    summarized: bool = False
    truncated: bool = False
    omitted_hunks_count: Optional[int] = None

    # Submodule data
    submodule: Optional[dict] = None

    # Diff hunks
    hunks: List[DiffHunk] = None

    def __post_init__(self) -> None:
        """Initialize hunks list if not provided."""
        if self.hunks is None:
            self.hunks = []


class DiffProcessor:
    """Processes unified diffs into structured hunks."""

    def __init__(self):
        """Initialize diff processor."""
        self.hunk_header_pattern = re.compile(
            r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@"
        )

    def process_file_change(
        self, change: FileChange, unified_diff: str
    ) -> ProcessedFile:
        """Process a file change into a structured format."""
        logger.debug(
            "Processing file change",
            extra={
                "status": change.status,
                "path_new": change.path_new,
                "path_old": change.path_old,
                "binary": change.is_binary,
                "submodule": change.is_submodule,
            },
        )

        processed = ProcessedFile(
            status=change.status,
            path_old=change.path_old,
            path_new=change.path_new,
            rename_score=change.rename_score,
            rename_tiebreaker=change.rename_tiebreaker,
            mode_old=change.mode_old,
            mode_new=change.mode_new,
            size_old=change.size_old,
            size_new=change.size_new,
            is_binary=change.is_binary,
            is_submodule=change.is_submodule,
        )

        if change.is_submodule:
            processed.submodule = {
                "old_sha": change.submodule_old_sha,
                "new_sha": change.submodule_new_sha,
            }

        if not change.is_binary and not change.is_submodule and unified_diff:
            processed.hunks = self._split_into_hunks(unified_diff)
            processed.eol_only_change = self._detect_eol_only_change(unified_diff)
            processed.whitespace_only_change = self._detect_whitespace_only_change(
                unified_diff
            )

        logger.debug(
            "Processed file",
            extra={
                "path": processed.path_new or processed.path_old,
                "hunks": len(processed.hunks) if processed.hunks else 0,
                "eol_only": processed.eol_only_change,
                "whitespace_only": processed.whitespace_only_change,
            },
        )
        return processed

    def _split_into_hunks(self, unified_diff: str) -> List[DiffHunk]:
        """Split unified diff into individual hunks."""
        hunks = []
        lines = unified_diff.split("\n")

        current_hunk_lines: List[str] = []
        current_header = None
        current_header_match = None

        for line in lines:
            header_match = self.hunk_header_pattern.match(line)
            if header_match:
                if current_header and current_hunk_lines:
                    hunk = self._create_hunk(
                        current_header, current_header_match, current_hunk_lines
                    )
                    if hunk:
                        hunks.append(hunk)

                current_header = line
                current_header_match = header_match
                current_hunk_lines = []
            elif current_header:
                current_hunk_lines.append(line)

        if current_header and current_hunk_lines:
            hunk = self._create_hunk(
                current_header, current_header_match, current_hunk_lines
            )
            if hunk:
                hunks.append(hunk)

        logger.debug("Split unified diff into %s hunks", len(hunks))
        return hunks

    def _create_hunk(
        self, header: str, header_match: re.Match, lines: List[str]
    ) -> Optional[DiffHunk]:
        """Create a DiffHunk from header and lines."""
        old_start = int(header_match.group(1))
        old_lines = int(header_match.group(2) or "1")
        new_start = int(header_match.group(3))
        new_lines = int(header_match.group(4) or "1")

        added = 0
        deleted = 0
        patch_lines = [header]

        for line in lines:
            if line.startswith("+") and not line.startswith("+++"):
                added += 1
            elif line.startswith("-") and not line.startswith("---"):
                deleted += 1
            patch_lines.append(line)

        patch = "\n".join(patch_lines)

        return DiffHunk(
            header=header,
            old_start=old_start,
            old_lines=old_lines,
            new_start=new_start,
            new_lines=new_lines,
            added=added,
            deleted=deleted,
            patch=patch,
        )

    def _detect_eol_only_change(self, unified_diff: str) -> bool:
        """Detect if change is only end-of-line differences."""
        lines = unified_diff.split("\n")
        removed = [
            line[1:]
            for line in lines
            if line.startswith("-") and not line.startswith("---")
        ]
        added = [
            line[1:]
            for line in lines
            if line.startswith("+") and not line.startswith("+++")
        ]

        if not removed and not added:
            return False

        if len(removed) != len(added):
            return False

        def _normalize(values: List[str]) -> str:
            normalized = "\n".join(values)
            normalized = normalized.replace("\r\n", "\n").replace("\r", "")
            return normalized

        if _normalize(removed) == _normalize(added):
            logger.debug("Detected EOL-only change via normalization")
            return True

        suffix_pairs = (("CRLF", "LF"), ("CR", ""), ("LF", ""))

        for old_line, new_line in zip(removed, added):
            old_base = old_line.rstrip("\r\n")
            new_base = new_line.rstrip("\r\n")

            if old_base == new_base:
                continue

            matched = False
            for old_suffix, new_suffix in suffix_pairs:
                old_matches = not old_suffix or old_base.endswith(old_suffix)
                new_matches = not new_suffix or new_base.endswith(new_suffix)
                if not (old_matches and new_matches):
                    continue

                old_stem = old_base[: -len(old_suffix)] if old_suffix else old_base
                new_stem = new_base[: -len(new_suffix)] if new_suffix else new_base

                if old_stem == new_stem:
                    matched = True
                    break

            if not matched:
                logger.debug(
                    "Change includes content differences beyond EOL",
                    extra={"old": old_line, "new": new_line},
                )
                return False

        logger.debug("Detected EOL-only change via suffix comparison")
        return True

    def _detect_whitespace_only_change(self, unified_diff: str) -> bool:
        """Detect if change is only whitespace differences."""
        lines = unified_diff.split("\n")
        old_content = []
        new_content = []

        for line in lines:
            if line.startswith("-") and not line.startswith("---"):
                old_content.append(line[1:])
            elif line.startswith("+") and not line.startswith("+++"):
                new_content.append(line[1:])

        if not old_content and not new_content:
            return False

        old_normalized = "".join("".join(line.split()) for line in old_content)
        new_normalized = "".join("".join(line.split()) for line in new_content)

        result = old_normalized == new_normalized and old_content != new_content
        if result:
            logger.debug("Detected whitespace-only change")
        else:
            logger.debug("Change includes substantive differences")
        return result
