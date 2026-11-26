#!/usr/bin/env python3
"""Fail unless the git tag, project version, ``__version__`` and CHANGELOG agree.

The tag must be ``v<version>`` where ``<version>`` is ``[project].version`` in ``pyproject.toml``.

    python scripts/check_release.py v2027.0.0.1
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION_FORMAT = re.compile(r"\d{4}\.\d+\.\d+\.\d+")


def check(tag: str | None) -> list[str]:
    """Return a list of consistency errors (empty when the release is consistent)."""
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    version: str = data["project"]["version"]
    errors: list[str] = []

    if not VERSION_FORMAT.fullmatch(version):
        errors.append(f"version {version!r} is not 'YYYY.MAJOR.MINOR.PATCH'")
    if tag is not None and tag != f"v{version}":
        errors.append(f"tag {tag!r} does not match version {version!r} (expected v{version})")

    cz_version = data.get("tool", {}).get("commitizen", {}).get("version")
    if cz_version != version:
        errors.append(f"[tool.commitizen] version {cz_version!r} != project version {version!r}")

    init_text = (ROOT / "src" / "lib_6107" / "__init__.py").read_text(encoding="utf-8")
    found = re.search(r'^__version__\s*=\s*"([^"]+)"', init_text, re.MULTILINE)
    if not found or found.group(1) != version:
        errors.append(f"__version__ {found.group(1) if found else None!r} != project version {version!r}")

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if not re.search(rf"^## v?{re.escape(version)}(?:[\s\-].*)?$", changelog, re.MULTILINE):
        errors.append(f"CHANGELOG.md has no '## v{version}' section")
    return errors


def main() -> int:
    """Run the check; tag is optional first argument."""
    tag = sys.argv[1] if len(sys.argv) > 1 else None
    errors = check(tag)
    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    if not errors:
        print("release check OK")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
