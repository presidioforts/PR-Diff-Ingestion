"""Tests for file policies module."""

import pytest

from p1diff.policies import FilePolicies


class TestFilePolicies:
    """Test FilePolicies class."""

    def test_is_lockfile(self):
        """Test lockfile detection."""
        # JavaScript/Node.js lockfiles
        assert FilePolicies.is_lockfile("package-lock.json") is True
        assert FilePolicies.is_lockfile("yarn.lock") is True
        assert FilePolicies.is_lockfile("pnpm-lock.yaml") is True
        assert FilePolicies.is_lockfile("npm-shrinkwrap.json") is True

        # Python lockfiles
        assert FilePolicies.is_lockfile("poetry.lock") is True
        assert FilePolicies.is_lockfile("Pipfile.lock") is True

        # Other language lockfiles
        assert FilePolicies.is_lockfile("gradle.lockfile") is True
        assert FilePolicies.is_lockfile("Gemfile.lock") is True
        assert FilePolicies.is_lockfile("composer.lock") is True
        assert FilePolicies.is_lockfile("Cargo.lock") is True
        assert FilePolicies.is_lockfile("go.sum") is True
        assert FilePolicies.is_lockfile("Package.resolved") is True
        assert FilePolicies.is_lockfile("mix.lock") is True
        assert FilePolicies.is_lockfile("packages.lock.json") is True

        # Non-lockfiles
        assert FilePolicies.is_lockfile("package.json") is False
        assert FilePolicies.is_lockfile("requirements.txt") is False
        assert FilePolicies.is_lockfile("main.py") is False

    def test_is_lockfile_with_path(self):
        """Test lockfile detection with full paths."""
        assert FilePolicies.is_lockfile("src/package-lock.json") is True
        assert FilePolicies.is_lockfile("frontend/yarn.lock") is True
        assert FilePolicies.is_lockfile("backend/poetry.lock") is True
        assert FilePolicies.is_lockfile("some/deep/path/Cargo.lock") is True

    def test_is_minified(self):
        """Test minified file detection."""
        assert FilePolicies.is_minified("script.min.js") is True
        assert FilePolicies.is_minified("style.min.css") is True
        assert FilePolicies.is_minified("app.min.js") is True

        # With paths
        assert FilePolicies.is_minified("dist/app.min.js") is True
        assert FilePolicies.is_minified("assets/style.min.css") is True

        # Non-minified
        assert FilePolicies.is_minified("script.js") is False
        assert FilePolicies.is_minified("style.css") is False
        assert FilePolicies.is_minified("app.ts") is False

    def test_is_source_map(self):
        """Test source map detection."""
        assert FilePolicies.is_source_map("script.js.map") is True
        assert FilePolicies.is_source_map("style.css.map") is True
        assert FilePolicies.is_source_map("app.map") is True

        # With paths
        assert FilePolicies.is_source_map("dist/app.js.map") is True
        assert FilePolicies.is_source_map("assets/style.css.map") is True

        # Non-source maps
        assert FilePolicies.is_source_map("script.js") is False
        assert FilePolicies.is_source_map("style.css") is False
        assert FilePolicies.is_source_map("config.json") is False

    def test_is_generated_file(self):
        """Test generated file detection."""
        # Lockfiles
        assert FilePolicies.is_generated_file("package-lock.json") is True
        assert FilePolicies.is_generated_file("yarn.lock") is True

        # Minified files
        assert FilePolicies.is_generated_file("app.min.js") is True
        assert FilePolicies.is_generated_file("style.min.css") is True

        # Source maps
        assert FilePolicies.is_generated_file("app.js.map") is True
        assert FilePolicies.is_generated_file("style.css.map") is True

        # Regular files
        assert FilePolicies.is_generated_file("main.py") is False
        assert FilePolicies.is_generated_file("index.html") is False
        assert FilePolicies.is_generated_file("script.js") is False

    def test_should_summarize_when_oversized(self):
        """Test summarization policy for oversized files."""
        # Generated files should be summarized
        assert FilePolicies.should_summarize_when_oversized("package-lock.json") is True
        assert FilePolicies.should_summarize_when_oversized("app.min.js") is True
        assert FilePolicies.should_summarize_when_oversized("style.js.map") is True

        # Regular files should not be summarized
        assert FilePolicies.should_summarize_when_oversized("main.py") is False
        assert FilePolicies.should_summarize_when_oversized("index.html") is False
        assert FilePolicies.should_summarize_when_oversized("script.js") is False

    def test_get_file_category(self):
        """Test file category classification."""
        assert FilePolicies.get_file_category("package-lock.json") == "lockfile"
        assert FilePolicies.get_file_category("yarn.lock") == "lockfile"

        assert FilePolicies.get_file_category("app.min.js") == "minified"
        assert FilePolicies.get_file_category("style.min.css") == "minified"

        assert FilePolicies.get_file_category("app.js.map") == "source_map"
        assert FilePolicies.get_file_category("style.css.map") == "source_map"

        assert FilePolicies.get_file_category("main.py") == "regular"
        assert FilePolicies.get_file_category("index.html") == "regular"
        assert FilePolicies.get_file_category("script.js") == "regular"
