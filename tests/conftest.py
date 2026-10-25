"""Pytest configuration and shared fixtures."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make the project root importable for tests
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from network_lab.core import NetworkScenario, default_scenario  # noqa: E402


@pytest.fixture
def scenario() -> NetworkScenario:
    return default_scenario()


@pytest.fixture
def empty_scenario() -> NetworkScenario:
    return NetworkScenario("Empty")
