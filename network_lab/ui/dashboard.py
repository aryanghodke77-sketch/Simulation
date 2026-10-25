"""Dashboard UI component.

Shows the current scenario summary, topology, and key metrics at a glance.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import streamlit as st

from network_lab.core.models import NetworkScenario
from network_lab.core.protocols import Packet, ProtocolEvent, SimulationResult


def render_dashboard(scenario: NetworkScenario) -> None:
    st.header("Dashboard")

    summary = scenario.summary()
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Devices", summary["devices"])
    col2.metric("Links", summary["links"])
    col3.metric("Subnets", summary["subnets"])
    col4.metric("Packets", summary["packets"])
    col5.metric("Protocol Events", summary["protocol_events"])
    col6.metric("Simulations", summary["simulation_results"])

    st.subheader("Topology")

    if not scenario.devices:
        st.info("No devices in the scenario yet. Add devices in the Scenario Builder.")
        return

    # Render a simple topology diagram using a table-driven layout
    _render_topology(scenario)


def _render_topology(scenario: NetworkScenario) -> None:
    """Render a simple textual/structured topology view."""
    cols = st.columns(max(1, len(scenario.devices)))
    for idx, (name, dev) in enumerate(scenario.devices.items()):
        with cols[idx % len(cols)]:
            st.markdown(f"**{dev.kind.capitalize()}** `{name}`")
            iface_lines = []
            for iface in dev.interfaces.values():
                iface_lines.append(f"- {iface.name}: {iface.ip or 'no IP'}")
            st.text("\n".join(iface_lines) if iface_lines else "- no interfaces")

    if scenario.links:
        st.subheader("Links")
        for link in scenario.links:
            st.markdown(f"`{link.a}:{link.a_iface}`  <->  `{link.b}:{link.b_iface}`")

    # Mini path preview: show a reachable pair when one exists
    names = list(scenario.devices.keys())
    if len(names) >= 2:
        shown = False
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                try:
                    path = scenario.find_path_names(a, b)
                    st.subheader("Path preview")
                    st.markdown(f"**{a}** → " + " → ".join(path[1:]))
                    shown = True
                    break
                except ValueError:
                    continue
            if shown:
                break
        if not shown:
            st.caption("No reachable path between any two devices.")
