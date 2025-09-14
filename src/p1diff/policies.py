"""File type policies and detection for P1 Diff tool."""

import os
from pathlib import Path
from typing import Set


class FilePolicies:
    """Policies for handling different file types."""

    # Lockfiles and generated files that should be summarized when oversized
    LOCKFILES = {
        # JavaScript/Node.js
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "npm-shrinkwrap.json",
        # Python
        "poetry.lock",
        "Pipfile.lock",
        # Java
        "gradle.lockfile",
        # Ruby
        "Gemfile.lock",
        # PHP
        "composer.lock",
        # Rust
        "Cargo.lock",
        # Go
        "go.sum",
        # Swift
        "Package.resolved",
        # Elixir
        "mix.lock",
        # .NET
        "packages.lock.json",
    }

    # File extensions for minified/generated files
    MINIFIED_EXTENSIONS = {".min.js", ".min.css"}
    MAP_EXTENSIONS = {".map", ".js.map", ".css.map"}

    @classmethod
    def is_lockfile(cls, file_path: str) -> bool:
        """Check if file is a lockfile."""
        filename = os.path.basename(file_path)
        return filename in cls.LOCKFILES

    @classmethod
    def is_minified(cls, file_path: str) -> bool:
        """Check if file is minified."""
        path = Path(file_path)
        return any(
            path.name.endswith(ext) or path.suffix in cls.MINIFIED_EXTENSIONS
            for ext in cls.MINIFIED_EXTENSIONS
        )

    @classmethod
    def is_source_map(cls, file_path: str) -> bool:
        """Check if file is a source map."""
        path = Path(file_path)
        return any(
            path.name.endswith(ext) or path.suffix in cls.MAP_EXTENSIONS
            for ext in cls.MAP_EXTENSIONS
        )

    @classmethod
    def is_generated_file(cls, file_path: str) -> bool:
        """Check if file is likely generated."""
        return (
            cls.is_lockfile(file_path)
            or cls.is_minified(file_path)
            or cls.is_source_map(file_path)
        )

    @classmethod
    def should_summarize_when_oversized(cls, file_path: str) -> bool:
        """Check if file should be summarized instead of truncated when oversized."""
        return cls.is_generated_file(file_path)

    @classmethod
    def get_file_category(cls, file_path: str) -> str:
        """Get category of file for notes/logging."""
        if cls.is_lockfile(file_path):
            return "lockfile"
        elif cls.is_minified(file_path):
            return "minified"
        elif cls.is_source_map(file_path):
            return "source_map"
        else:
            return "regular"
