"""Capacity management and truncation logic for P1 Diff tool."""

from typing import List, Tuple

from .config import DiffConfig
from .diffpack import DiffHunk, ProcessedFile
from .policies import FilePolicies


class CapacityManager:
    """Manages file and global capacity limits with truncation logic."""

    def __init__(self, config: DiffConfig):
        """Initialize with configuration."""
        self.config = config
        self.total_bytes_used = 0
        self.omitted_files_count = 0

    def apply_caps(self, files: List[ProcessedFile]) -> Tuple[List[ProcessedFile], int]:
        """Apply capacity limits to files and return processed files and omitted count."""
        processed_files = []
        self.total_bytes_used = 0
        self.omitted_files_count = 0

        for file in files:
            # Calculate file size
            file_size = self._calculate_file_size(file)

            # Check global cap
            if self.total_bytes_used + file_size > self.config.cap_total:
                # Exceed global cap - include metadata only
                file.hunks = []
                file.omitted_hunks_count = len(file.hunks) if file.hunks else 0
                self.omitted_files_count += 1
                processed_files.append(file)
                continue

            # Apply per-file cap
            if file_size > self.config.cap_file:
                file = self._apply_per_file_cap(file)

            processed_files.append(file)
            self.total_bytes_used += self._calculate_file_size(file)

        return processed_files, self.omitted_files_count

    def _calculate_file_size(self, file: ProcessedFile) -> int:
        """Calculate the size of a file's patch content in UTF-8 bytes."""
        if not file.hunks:
            return 0

        total_size = 0
        for hunk in file.hunks:
            total_size += len(hunk.patch.encode("utf-8"))

        return total_size

    def _apply_per_file_cap(self, file: ProcessedFile) -> ProcessedFile:
        """Apply per-file capacity limit with intelligent truncation."""
        if not file.hunks:
            return file

        # Check if this is a generated file that should be summarized
        file_path = file.path_new or file.path_old
        if file_path and FilePolicies.should_summarize_when_oversized(file_path):
            file.summarized = True
            file.hunks = []
            file.omitted_hunks_count = len(file.hunks)
            return file

        # Apply truncation logic: keep first and last hunks, truncate middle
        original_hunk_count = len(file.hunks)
        truncated_hunks = []
        current_size = 0
        omitted_count = 0

        # Always try to include first hunk
        if file.hunks:
            first_hunk = file.hunks[0]
            first_size = len(first_hunk.patch.encode("utf-8"))
            if first_size <= self.config.cap_file:
                truncated_hunks.append(first_hunk)
                current_size += first_size

        # Try to include last hunk if different from first
        if len(file.hunks) > 1:
            last_hunk = file.hunks[-1]
            last_size = len(last_hunk.patch.encode("utf-8"))
            if current_size + last_size <= self.config.cap_file:
                # Reserve space for last hunk
                remaining_space = self.config.cap_file - current_size - last_size
                
                # Try to include middle hunks
                for i, hunk in enumerate(file.hunks[1:-1], 1):
                    hunk_size = len(hunk.patch.encode("utf-8"))
                    if hunk_size <= remaining_space:
                        truncated_hunks.append(hunk)
                        remaining_space -= hunk_size
                    else:
                        # Try to include a truncated version with reduced context
                        truncated_hunk = self._truncate_hunk_context(hunk, remaining_space)
                        if truncated_hunk:
                            truncated_hunks.append(truncated_hunk)
                            break
                        else:
                            omitted_count += 1

                # Add remaining omitted hunks to count
                omitted_count += len(file.hunks) - len(truncated_hunks) - 1

                # Add last hunk
                truncated_hunks.append(last_hunk)
            else:
                # Can't fit last hunk, count all remaining as omitted
                omitted_count = len(file.hunks) - len(truncated_hunks)

        # Update file with truncated hunks
        if omitted_count > 0:
            file.truncated = True
            file.omitted_hunks_count = omitted_count

        file.hunks = truncated_hunks
        return file

    def _truncate_hunk_context(self, hunk: DiffHunk, max_size: int) -> DiffHunk:
        """Truncate hunk context to fit within size limit."""
        lines = hunk.patch.split("\n")
        if len(lines) <= 3:  # Header + minimal content
            return None

        # Keep header and try to reduce context
        header_line = lines[0]
        content_lines = lines[1:]

        # Separate context, added, and deleted lines
        context_lines = []
        change_lines = []

        for line in content_lines:
            if line.startswith(("+", "-")):
                change_lines.append(line)
            else:
                context_lines.append(line)

        # Try with minimal context (1 line before/after changes)
        if len(context_lines) > 2:
            # Keep first and last context line only
            minimal_lines = [header_line]
            if context_lines:
                minimal_lines.append(context_lines[0])
            minimal_lines.extend(change_lines)
            if len(context_lines) > 1:
                minimal_lines.append(context_lines[-1])

            minimal_patch = "\n".join(minimal_lines)
            if len(minimal_patch.encode("utf-8")) <= max_size:
                return DiffHunk(
                    header=hunk.header,
                    old_start=hunk.old_start,
                    old_lines=hunk.old_lines,
                    new_start=hunk.new_start,
                    new_lines=hunk.new_lines,
                    added=hunk.added,
                    deleted=hunk.deleted,
                    patch=minimal_patch,
                )

        return None
