"""Service layer for P1 Diff API."""

import logging
from typing import Dict, Any, Optional

from ...caps import CapacityManager
from ...config import DiffConfig
from ...diffpack import DiffProcessor
from ...errors import P1DiffError
from ...serialize import DeterministicSerializer
from ...vcs import GitRepository


logger = logging.getLogger(__name__)


def collect_notes(
    files: list,
    omitted_files_count: int,
    eol_changes: int,
    whitespace_changes: int,
    summarized_lockfiles: int,
) -> list:
    """Collect notes about the diff processing."""
    notes = []

    if omitted_files_count > 0:
        notes.append(f"Omitted {omitted_files_count} files due to capacity limits")

    if eol_changes > 0:
        notes.append(f"{eol_changes} files with only EOL changes")

    if whitespace_changes > 0:
        notes.append(f"{whitespace_changes} files with only whitespace changes")

    if summarized_lockfiles > 0:
        notes.append(f"{summarized_lockfiles} lockfiles summarized due to size")

    return notes


class DiffService:
    """Service class that encapsulates the core diff processing logic."""

    def process_diff_request(
        self,
        repo_url: str,
        commit_good: str,
        commit_candidate: str,
        branch_name: Optional[str] = None,
        cap_total: int = 800000,
        cap_file: int = 64000,
        context_lines: int = 3,
        find_renames_threshold: int = 90,
    ) -> Dict[str, Any]:
        """Process a diff request and return the complete JSON response."""
        logger.info(
            "Processing diff request",
            extra={"repo": repo_url, "good": commit_good, "candidate": commit_candidate},
        )

        try:
            config = DiffConfig(
                repo_url=repo_url,
                commit_good=commit_good,
                commit_candidate=commit_candidate,
                branch_name=branch_name,
                cap_total=cap_total,
                cap_file=cap_file,
                context_lines=context_lines,
                find_renames_threshold=find_renames_threshold,
            )

            payload = self._process_diff_core(config)

            serializer = DeterministicSerializer(config)
            result = serializer.create_success_envelope(payload)

            logger.info(
                "Diff processing succeeded",
                extra={
                    "repo": repo_url,
                    "files": len(payload.get("files", [])),
                    "notes": len(payload.get("notes", [])),
                },
            )

            return result

        except P1DiffError as exc:
            logger.warning(
                "Known P1 diff error",
                extra={"repo": repo_url, "code": exc.code},
            )
            serializer = DeterministicSerializer(DiffConfig("", "", ""))
            return serializer.create_error_envelope(exc.code, exc.message, exc.details)

        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("Unexpected error during diff processing", extra={"repo": repo_url})
            serializer = DeterministicSerializer(DiffConfig("", "", ""))
            return serializer.create_error_envelope(
                "INTERNAL_ERROR",
                f"Internal error: {str(exc)}",
                {"exception_type": type(exc).__name__},
            )

    def _process_diff_core(self, config: DiffConfig) -> Dict[str, Any]:
        """Core diff processing logic shared by the API."""
        logger.debug("Initializing Git repository", extra={"repo": config.repo_url})
        with GitRepository(config) as repo:
            repo.clone_and_setup()
            logger.info("Repository cloned", extra={"repo": config.repo_url})
            git_version = repo.validate_git_version()

            file_changes = repo.get_file_changes()
            logger.info(
                "Collected file changes",
                extra={"repo": config.repo_url, "changes": len(file_changes)},
            )

            diff_processor = DiffProcessor()
            processed_files = []

            for change in file_changes:
                logger.debug(
                    "Processing change",
                    extra={
                        "repo": config.repo_url,
                        "path": change.path_new or change.path_old,
                        "status": change.status,
                    },
                )
                unified_diff = ""
                if not change.is_binary and not change.is_submodule:
                    unified_diff = repo.get_unified_diff(change)

                processed_file = diff_processor.process_file_change(change, unified_diff)
                processed_files.append(processed_file)

            capacity_manager = CapacityManager(config)
            final_files, omitted_files_count = capacity_manager.apply_caps(processed_files)
            logger.info(
                "Capacity management applied",
                extra={
                    "repo": config.repo_url,
                    "files_returned": len(final_files),
                    "omitted_files": omitted_files_count,
                },
            )

            eol_changes = sum(1 for f in final_files if f.eol_only_change)
            whitespace_changes = sum(1 for f in final_files if f.whitespace_only_change)
            summarized_lockfiles = sum(1 for f in final_files if f.summarized)

            notes = collect_notes(
                final_files,
                omitted_files_count,
                eol_changes,
                whitespace_changes,
                summarized_lockfiles,
            )

            serializer = DeterministicSerializer(config)
            payload = serializer.serialize_output(
                final_files, omitted_files_count, notes, git_version
            )

            logger.info(
                "Serialization complete",
                extra={
                    "repo": config.repo_url,
                    "files": len(final_files),
                    "notes": len(notes),
                    "git_version": git_version,
                },
            )

            return payload
