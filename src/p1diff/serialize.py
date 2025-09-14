"""Deterministic serialization for P1 Diff tool."""

import hashlib
import json
from typing import Any, Dict, List

from .config import DiffConfig
from .diffpack import ProcessedFile


class DeterministicSerializer:
    """Handles deterministic JSON serialization with stable ordering."""

    def __init__(self, config: DiffConfig):
        """Initialize with configuration."""
        self.config = config

    def serialize_output(
        self,
        files: List[ProcessedFile],
        omitted_files_count: int,
        notes: List[str],
        git_version: str,
    ) -> Dict[str, Any]:
        """Serialize the complete output to a deterministic dictionary."""
        # Build provenance
        provenance = self.config.to_provenance_dict()
        provenance["git_version"] = git_version

        # Build files array
        files_data = []
        for file in files:
            file_data = self._serialize_file(file)
            files_data.append(file_data)

        # Sort files deterministically
        files_data.sort(key=self._file_sort_key)

        # Build complete payload
        payload = {
            "provenance": provenance,
            "files": files_data,
            "omitted_files_count": omitted_files_count,
            "notes": sorted(notes),  # Ensure notes are sorted
        }

        # Compute checksum
        checksum = self._compute_checksum(payload)
        payload["provenance"]["checksum"] = checksum

        return payload

    def _serialize_file(self, file: ProcessedFile) -> Dict[str, Any]:
        """Serialize a single file to dictionary."""
        file_data = {
            "status": file.status,
            "path_old": file.path_old,
            "path_new": file.path_new,
            "mode_old": file.mode_old,
            "mode_new": file.mode_new,
            "size_old": file.size_old,
            "size_new": file.size_new,
            "is_binary": file.is_binary,
            "is_submodule": file.is_submodule,
        }

        # Add optional fields only if they have meaningful values
        if file.rename_score is not None:
            file_data["rename_score"] = file.rename_score

        if file.rename_tiebreaker is not None:
            file_data["rename_tiebreaker"] = file.rename_tiebreaker

        if file.eol_only_change:
            file_data["eol_only_change"] = True

        if file.whitespace_only_change:
            file_data["whitespace_only_change"] = True

        if file.summarized:
            file_data["summarized"] = True

        if file.truncated:
            file_data["truncated"] = True

        if file.omitted_hunks_count is not None and file.omitted_hunks_count > 0:
            file_data["omitted_hunks_count"] = file.omitted_hunks_count

        if file.submodule:
            file_data["submodule"] = file.submodule

        # Add hunks if present
        if file.hunks:
            hunks_data = []
            for hunk in file.hunks:
                hunk_data = {
                    "header": hunk.header,
                    "old_start": hunk.old_start,
                    "old_lines": hunk.old_lines,
                    "new_start": hunk.new_start,
                    "new_lines": hunk.new_lines,
                    "added": hunk.added,
                    "deleted": hunk.deleted,
                    "patch": hunk.patch,
                }
                hunks_data.append(hunk_data)

            # Sort hunks by position
            hunks_data.sort(key=lambda h: (h["old_start"], h["new_start"]))
            file_data["hunks"] = hunks_data

        return file_data

    def _file_sort_key(self, file_data: Dict[str, Any]) -> tuple:
        """Generate sort key for file ordering."""
        # Sort by effective new path (fallback to old), then by status
        effective_path = file_data.get("path_new") or file_data.get("path_old") or ""
        status = file_data.get("status", "")
        return (effective_path, status)

    def _compute_checksum(self, payload: Dict[str, Any]) -> str:
        """Compute SHA-256 checksum of the payload."""
        # Create a copy without the checksum field
        payload_copy = self._deep_copy_without_checksum(payload)

        # Serialize to JSON with deterministic ordering
        json_bytes = self._to_deterministic_json_bytes(payload_copy)

        # Compute SHA-256
        return hashlib.sha256(json_bytes).hexdigest()

    def _deep_copy_without_checksum(self, obj: Any) -> Any:
        """Deep copy object, removing checksum field from provenance."""
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                if key == "provenance":
                    # Copy provenance but exclude checksum
                    provenance_copy = {}
                    for pkey, pvalue in value.items():
                        if pkey != "checksum":
                            provenance_copy[pkey] = self._deep_copy_without_checksum(pvalue)
                    result[key] = provenance_copy
                else:
                    result[key] = self._deep_copy_without_checksum(value)
            return result
        elif isinstance(obj, list):
            return [self._deep_copy_without_checksum(item) for item in obj]
        else:
            return obj

    def _to_deterministic_json_bytes(self, obj: Any) -> bytes:
        """Convert object to deterministic JSON bytes."""
        json_str = json.dumps(
            obj,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            indent=None,
        )
        return json_str.encode("utf-8", errors="replace")

    def to_json_string(self, payload: Dict[str, Any]) -> str:
        """Convert payload to pretty-printed JSON string."""
        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )

    def create_success_envelope(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create success envelope around payload."""
        return {"ok": True, "data": payload}

    def create_error_envelope(self, error_code: str, error_message: str, details: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create error envelope."""
        error_data = {
            "code": error_code,
            "message": error_message,
        }
        if details:
            error_data["details"] = details

        return {"ok": False, "error": error_data}
