"""Pytest configuration for the in-progress RobotPy 2027 / Systemcore port.

Modules listed in ``collect_ignore`` fail at import time against the 2027 libraries, so the
``@pytest.mark.skip`` decorator alone cannot hide them. Remove an entry here as soon as the
code under test is ported and the tests are re-enabled.
"""

collect_ignore = [
    "util/test_competition.py",  # lib_6107.util.competition was removed from the library
]
