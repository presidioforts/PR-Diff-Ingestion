"""Service layer for P1 Diff API - extracts core logic from CLI."""

from typing import Dict, Any, Optional
from ..caps import CapacityManager
from ..config import DiffConfig
from ..diffpack import DiffProcessor
from ..errors import P1DiffError
from ..serialize import DeterministicSerializer
from ..vcs import GitRepository


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
        """
        Process a diff request and return the complete JSON response.
        
        This method replicates the exact logic from the CLI main.py but
        returns the result directly instead of outputting to stdout/file.
        
        Returns:
            Dict containing the exact same structure as test_output.json
        """
        try:
            # Create configuration (same as CLI)
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
            
            # Process diff (exact same logic as CLI)
            payload = self._process_diff_core(config)
            
            # Create success envelope (same as CLI)
            serializer = DeterministicSerializer(config)
            result = serializer.create_success_envelope(payload)
            
            return result
            
        except P1DiffError as e:
            # Handle known P1 Diff errors (same as CLI)
            serializer = DeterministicSerializer(DiffConfig("", "", ""))
            result = serializer.create_error_envelope(e.code, e.message, e.details)
            return result
            
        except Exception as e:
            # Handle unexpected errors (same as CLI)
            serializer = DeterministicSerializer(DiffConfig("", "", ""))
            result = serializer.create_error_envelope(
                "INTERNAL_ERROR",
                f"Internal error: {str(e)}",
                {"exception_type": type(e).__name__}
            )
            return result
    
    def _process_diff_core(self, config: DiffConfig) -> Dict[str, Any]:
        """Core diff processing logic extracted from CLI main.py."""
        with GitRepository(config) as repo:
            # Clone and setup
            repo.clone_and_setup()
            git_version = repo.validate_git_version()

            # Get file changes
            file_changes = repo.get_file_changes()

            # Process each file
            diff_processor = DiffProcessor()
            processed_files = []

            for change in file_changes:
                # Get unified diff for text files
                unified_diff = ""
                if not change.is_binary and not change.is_submodule:
                    unified_diff = repo.get_unified_diff(change)

                # Process the file
                processed_file = diff_processor.process_file_change(change, unified_diff)
                processed_files.append(processed_file)

            # Apply capacity limits
            capacity_manager = CapacityManager(config)
            final_files, omitted_files_count = capacity_manager.apply_caps(processed_files)

            # Collect statistics for notes
            eol_changes = sum(1 for f in final_files if f.eol_only_change)
            whitespace_changes = sum(1 for f in final_files if f.whitespace_only_change)
            summarized_lockfiles = sum(1 for f in final_files if f.summarized)

            # Generate notes
            notes = collect_notes(
                final_files,
                omitted_files_count,
                eol_changes,
                whitespace_changes,
                summarized_lockfiles,
            )

            # Serialize output
            serializer = DeterministicSerializer(config)
            payload = serializer.serialize_output(
                final_files, omitted_files_count, notes, git_version
            )

            return payload
