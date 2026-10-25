"""Session-state helpers for the Streamlit UI.

Provides a default scenario (PC1 -> Router -> PC2) so the dashboard
can be demonstrated immediately, plus helpers to reset/replace scenarios.
"""
from __future__ import annotations

from typing import Dict, Optional

from network_lab.core.models import NetworkScenario, Device


def default_scenario() -> NetworkScenario:
    """Build the canonical V0.1 demo scenario: PC1 - Router - PC2."""
    s = NetworkScenario("Lab 1: Simple routed network")
    s.add_device("PC1", "pc")
    s.add_device("Router", "router")
    s.add_device("PC2", "pc")

    # Connect on the interfaces that will carry the IPs, so the topology,
    # addressing, and path traversal are internally consistent.
    s.connect("PC1", "Router", a_iface="eth0", b_iface="eth0")
    s.connect("Router", "PC2", a_iface="eth1", b_iface="eth0")

    # Assign per-interface IPs to make the topology meaningful
    s.assign_ip("PC1", "eth0", "192.168.1.10")
    s.assign_ip("Router", "eth0", "192.168.1.1")
    s.assign_ip("Router", "eth1", "192.168.2.1")
    s.assign_ip("PC2", "eth0", "192.168.2.10")

    s.subnets["192.168.1.0/24"] = "LAN A (PC1 side)"
    s.subnets["192.168.2.0/24"] = "LAN B (PC2 side)"
    return s


def scenario_from_session(state: Dict) -> Optional[NetworkScenario]:
    sc = state.get("scenario")
    if isinstance(sc, NetworkScenario):
        return sc
    return None
