"""Pytest configuration for the in-progress RobotPy 2027 / Systemcore port.

Modules listed in ``collect_ignore`` fail at import time against the 2027 libraries, so the
``@pytest.mark.skip`` decorator alone cannot hide them. Remove an entry here as soon as the
code under test is ported and the tests are re-enabled.
"""

import pytest
from tunables import MockTunableBackend, TunableRegistry

collect_ignore = [
    "util/test_competition.py",  # lib_6107.util.competition was removed from the library
]


@pytest.fixture
def tunables_backend():
    """
    Provide a clean tunables registry backed by a ``MockTunableBackend``.

    Use ``backend.set_double("/Name", value)`` (or ``set_bool`` / ``set_string`` / ``set_int32``) followed by ``TunableRegistry.update()`` to simulate an Elastic write.
    The registry is reset before and after each test so tunable names can be reused.
    """
    TunableRegistry.reset()
    backend = MockTunableBackend()
    TunableRegistry.register_backend("", backend)
    yield backend
    TunableRegistry.reset()


@pytest.fixture(autouse=True)
def _clear_phoenix6_signals():
    from lib_6107.util.phoenix6.signals import Phoenix6Signals

    Phoenix6Signals.clear()
    yield
    Phoenix6Signals.clear()
