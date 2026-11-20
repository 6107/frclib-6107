"""Guard: pykit sources must not reference SmartDashboard/dashboards (2027 uses Elastic + tunables)."""

import re
from pathlib import Path

import lib_6107.pykit as pykit

ALLOWED = ("LoggedDashboardChooser", "loggeddashboardchooser")


def test_pykit_has_no_dashboard_references():
    root = Path(pykit.__file__).parent
    offenders = []
    for path in root.rglob("*.py"):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            cleaned = line
            for name in ALLOWED:
                cleaned = cleaned.replace(name, "")
            if re.search("dashboard", cleaned, re.IGNORECASE):
                offenders.append(f"{path.relative_to(root)}:{number}: {line.strip()}")
    assert not offenders, "\n".join(offenders)
