"""Main CLI entry point for P1 Diff tool."""

import argparse
import json
import sys
from pathlib import Path
from typing import List, Optional

from .caps import CapacityManager
from .config import DiffConfig
from .diffpack import DiffProcessor
from .errors import P1DiffError
from .serialize import DeterministicSerializer
from .vcs import GitRepository


def create_parser() -> argparse.ArgumentParser:
    """Create command line argument parser."""
    parser = argparse.ArgumentParser(
        prog="p1diff",
        description="Deterministic Git diff ingestion tool for code analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  p1diff --repo https://github.com/user/repo.git --good abc123 --cand def456
  p1diff --repo /path/to/repo --good v1.0 --cand v2.0 --json output.json
  p1diff --repo https://github.com/user/repo.git --good abc123 --cand def456 \\
         --cap-total 1000000 --cap-file 100000 --context 5 --find-renames 80
        """,
    )

    # Required arguments
    parser.add_argument(
        "--repo",
        required=True,
        help="Repository URL or local path",
    )
    parser.add_argument(
        "--good",
        required=True,
        help="Good commit SHA (baseline)",
    )
    parser.add_argument(
        "--cand",
        required=True,
        help="Candidate commit SHA (comparison target)",
    )

    # Optional arguments
    parser.add_argument(
        "--branch",
        help="Branch name (for metadata and fetch hint)",
    )
    parser.add_argument(
        "--cap-total",
        type=int,
        default=800_000,
        help="Total capacity limit in bytes (default: 800000)",
    )
    parser.add_argument(
        "--cap-file",
        type=int,
        default=64_000,
        help="Per-file capacity limit in bytes (default: 64000)",
    )
    parser.add_argument(
        "--context",
        type=int,
        default=3,
        help="Number of context lines in diffs (default: 3)",
    )
    parser.add_argument(
        "--find-renames",
        type=int,
        default=90,
        help="Rename detection threshold percentage (default: 90)",
    )
    parser.add_argument(
        "--json",
        help="Output JSON to file instead of stdout",
    )
    parser.add_argument(
        "--keep-workdir",
        action="store_true",
        help="Keep temporary work directory for debugging",
    )
    parser.add_argument(
        "--keep-on-error",
        action="store_true",
        help="Keep work directory on error for debugging",
    )

    return parser


def validate_args(args: argparse.Namespace) -> None:
    """Validate command line arguments."""
    if args.cap_total <= 0:
        raise ValueError("--cap-total must be positive")
    if args.cap_file <= 0:
        raise ValueError("--cap-file must be positive")
    if args.cap_file > args.cap_total:
        raise ValueError("--cap-file cannot exceed --cap-total")
    if args.context < 0:
        raise ValueError("--context cannot be negative")
    if not (0 <= args.find_renames <= 100):
        raise ValueError("--find-renames must be between 0 and 100")


def create_config(args: argparse.Namespace) -> DiffConfig:
    """Create configuration from command line arguments."""
    return DiffConfig(
        repo_url=args.repo,
        commit_good=args.good,
        commit_candidate=args.cand,
        branch_name=args.branch,
        cap_total=args.cap_total,
        cap_file=args.cap_file,
        context_lines=args.context,
        find_renames_threshold=args.find_renames,
        json_output_path=args.json,
        keep_workdir=args.keep_workdir,
        keep_on_error=args.keep_on_error,
    )


def collect_notes(
    files: List,
    omitted_files_count: int,
    eol_changes: int = 0,
    whitespace_changes: int = 0,
    summarized_lockfiles: int = 0,
) -> List[str]:
    """Collect notes about the processing."""
    notes = []

    if omitted_files_count > 0:
        notes.append(f"{omitted_files_count} files omitted due to global capacity limit")

    if summarized_lockfiles > 0:
        notes.append(f"{summarized_lockfiles} lockfiles summarized")

    if eol_changes > 0:
        notes.append(f"EOL changes detected in {eol_changes} files")

    if whitespace_changes > 0:
        notes.append(f"Whitespace-only changes in {whitespace_changes} files")

    return notes


def process_diff(config: DiffConfig) -> dict:
    """Process diff and return result payload."""
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


def output_result(result: dict, output_path: Optional[str]) -> None:
    """Output result to stdout or file."""
    serializer = DeterministicSerializer(DiffConfig("", "", ""))  # Dummy config for formatting
    json_str = serializer.to_json_string(result)

    if output_path:
        Path(output_path).write_text(json_str, encoding="utf-8")
    else:
        print(json_str)


def main() -> int:
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    try:
        # Validate arguments
        validate_args(args)

        # Create configuration
        config = create_config(args)

        # Process diff
        payload = process_diff(config)

        # Create success envelope
        serializer = DeterministicSerializer(config)
        result = serializer.create_success_envelope(payload)

        # Output result
        output_result(result, args.json)

        return 0

    except P1DiffError as e:
        # Handle known P1 Diff errors
        serializer = DeterministicSerializer(DiffConfig("", "", ""))  # Dummy config
        result = serializer.create_error_envelope(e.code, e.message, e.details)
        output_result(result, args.json)
        return 1

    except Exception as e:
        # Handle unexpected errors
        serializer = DeterministicSerializer(DiffConfig("", "", ""))  # Dummy config
        result = serializer.create_error_envelope(
            "INTERNAL_ERROR",
            f"Internal error: {str(e)}",
            {"type": type(e).__name__}
        )
        output_result(result, args.json)
        return 1


if __name__ == "__main__":
    sys.exit(main())
