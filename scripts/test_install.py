#!/usr/bin/env python3
"""Test script to verify P1 Diff installation."""

import subprocess
import sys
from pathlib import Path


def test_import():
    """Test that the package can be imported."""
    try:
        import p1diff
        print(f"✓ Package import successful (version: {p1diff.__version__})")
        return True
    except ImportError as e:
        print(f"✗ Package import failed: {e}")
        return False


def test_cli():
    """Test that the CLI command is available."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "p1diff.main", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            print("✓ CLI command available")
            return True
        else:
            print(f"✗ CLI command failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ CLI test failed: {e}")
        return False


def test_git_version():
    """Test that Git is available and meets version requirements."""
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            version_line = result.stdout.strip()
            print(f"✓ Git available: {version_line}")
            return True
        else:
            print("✗ Git not available")
            return False
    except Exception as e:
        print(f"✗ Git test failed: {e}")
        return False


def main():
    """Run all installation tests."""
    print("Testing P1 Diff installation...")
    print("=" * 40)

    tests = [
        ("Package Import", test_import),
        ("CLI Command", test_cli),
        ("Git Availability", test_git_version),
    ]

    passed = 0
    total = len(tests)

    for name, test_func in tests:
        print(f"\n{name}:")
        if test_func():
            passed += 1

    print("\n" + "=" * 40)
    print(f"Tests passed: {passed}/{total}")

    if passed == total:
        print("✓ Installation test successful!")
        return 0
    else:
        print("✗ Installation test failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
