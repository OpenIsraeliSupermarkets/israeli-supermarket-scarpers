#!/usr/bin/env python3
"""Fail if setup.py's static packages= list misses a shippable package.

Keeps the explicit list in setup.py, but compares it to find_packages() so a
new submodule with __init__.py cannot be forgotten before PyPI publish.
"""

from __future__ import annotations

import sys
from pathlib import Path

from setuptools import find_packages

# Roots we intend to ship (not e.g. scripts/).
SHIPPED_ROOTS = ("il_supermarket_scarper", "testing_util")
FIND_EXCLUDE = ("*.tests", "*.tests.*", "tests", "tests.*")


def _declared_packages(repo_root: Path) -> set[str]:
    """Load packages= from setup.py without building a dist."""
    captured: dict = {}

    def _capture_setup(**kwargs):
        captured.update(kwargs)

    import setuptools

    original = setuptools.setup
    setuptools.setup = _capture_setup
    try:
        # setup.py reads README/requirements relative to CWD.
        import runpy

        runpy.run_path(str(repo_root / "setup.py"), run_name="__not_main__")
    finally:
        setuptools.setup = original

    packages = captured.get("packages")
    if not isinstance(packages, list):
        raise RuntimeError("setup.py did not declare a packages= list")
    return set(packages)


def _discovered_shippable() -> set[str]:
    discovered = set(find_packages(exclude=list(FIND_EXCLUDE)))
    return {
        name
        for name in discovered
        if name in SHIPPED_ROOTS
        or any(name.startswith(f"{root}.") for root in SHIPPED_ROOTS)
    }


def check_setup_packages(repo_root: Path | None = None) -> None:
    """Raise AssertionError with a clear message if lists diverge."""
    root = repo_root or Path(__file__).resolve().parents[1]
    declared = _declared_packages(root)
    discovered = _discovered_shippable()

    missing = sorted(discovered - declared)
    extra = sorted(declared - discovered)

    errors = []
    if missing:
        errors.append(
            "Missing from setup.py packages= (add these):\n  - "
            + "\n  - ".join(missing)
        )
    if extra:
        errors.append(
            "Listed in setup.py packages= but not found on disk "
            "(remove or fix):\n  - " + "\n  - ".join(extra)
        )
    if errors:
        raise AssertionError("\n\n".join(errors))


def main() -> int:
    try:
        check_setup_packages()
    except AssertionError as exc:
        print(exc, file=sys.stderr)
        return 1
    print("setup.py packages= matches shippable find_packages() set.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
