"""Topology analysis helpers operating on a NetworkScenario.

Kept separate from core/models.py so path logic can grow without
polluting the domain object.
"""
from __future__ import annotations

from network_lab.core.models import NetworkScenario


def find_path(scenario: NetworkScenario, source: str, destination: str):
    """Convenience wrapper around NetworkScenario.find_path."""
    return scenario.find_path(source, destination)


def find_path_names(scenario: NetworkScenario, source: str, destination: str):
    return scenario.find_path_names(source, destination)


def is_reachable(scenario: NetworkScenario, source: str, destination: str) -> bool:
    try:
        find_path(scenario, source, destination)
        return True
    except ValueError:
        return False


def path_interfaces(scenario: NetworkScenario, source: str, destination: str):
    return scenario.interfaces_on_path(source, destination)


def hop_count(scenario: NetworkScenario, source: str, destination: str) -> int:
    """Number of links traversed (devices - 1)."""
    names = find_path_names(scenario, source, destination)
    return max(0, len(names) - 1)
