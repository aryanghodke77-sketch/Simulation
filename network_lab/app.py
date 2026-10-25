"""Network Lab — Streamlit application.

The single entry point for the Streamlit UI. Manages session state around
the NetworkScenario and routes to the various UI components.
"""
from __future__ import annotations

import streamlit as st

from network_lab.core.models import NetworkScenario
from network_lab.core.state import default_scenario
from network_lab.ui import dashboard, scenario as scenario_ui
from network_lab.ui import subnetting, packets, protocols, errors, bandwidth, evaluation
from network_lab.simulation.network import simulate_flow
from network_lab.simulation.traffic import TrafficFlow, SimulationConfig
from network_lab.modules.packets.generator import run_simulation


def main() -> None:
    st.set_page_config(page_title="Network Lab", layout="wide")
    st.title("Network Lab")

    # ---- session state init ----
    if "scenario" not in st.session_state:
        st.session_state["scenario"] = default_scenario()
        st.session_state["eval_participant"] = "anonymous"
        st.session_state["eval_session_id"] = "session-" + str(abs(hash(str(st.session_state))))
        st.session_state["eval_start_time"] = None

    scenario = st.session_state["scenario"]
    if not isinstance(scenario, NetworkScenario):
        scenario = default_scenario()
        st.session_state["scenario"] = scenario

    sidebar()
    tabs(scenario)


def sidebar() -> None:
    with st.sidebar:
        st.header("Scenario")
        name = st.text_input("Scenario name", value=st.session_state.scenario.name, key="sidebar_name")
        if name and name != st.session_state.scenario.name:
            st.session_state.scenario.name = name

        st.divider()
        st.caption("Current topology:")
        sc = st.session_state.scenario
        summary = sc.summary()
        st.markdown(
            f"- Devices: **{summary['devices']}**\n"
            f"- Links: **{summary['links']}**\n"
            f"- Subnets: **{summary['subnets']}**\n"
            f"- Packets: **{summary['packets']}**\n"
            f"- Events: **{summary['protocol_events']}**\n"
            f"- Simulations: **{summary['simulation_results']}**"
        )

        st.divider()
        st.caption("Quick actions")
        if st.button("Reset to demo scenario", key="reset_scenario"):
            st.session_state.scenario = default_scenario()
            st.session_state.scenario.name = st.session_state.get("sidebar_name", "Lab 1: Simple routed network")
            st.rerun()

        if st.button("Clear simulation data", key="clear_sim"):
            st.session_state.scenario.clear()
            st.rerun()

        st.divider()
        st.caption("About")
        st.markdown(
            """A teaching tool for network simulation.

Built around a single `NetworkScenario` model that coordinates devices,
topology, packets, protocols, errors, and bandwidth."""
        )


def tabs(scenario: NetworkScenario) -> None:
    tab_map = {
        "Dashboard": dashboard.render_dashboard,
        "Scenario Builder": scenario_ui.render_scenario_builder,
        "Subnetting": subnetting.render_subnetting,
        "Packet Analysis": packets.render_packet_analysis,
        "Protocol Visualization": protocols.render_protocol_visualization,
        "Error Detection": errors.render_error_detection,
        "Bandwidth": bandwidth.render_bandwidth,
        "Evaluation": evaluation.render_evaluation,
    }

    # Add a Simulator tab that drives the packet/protocol/bandwidth flow
    tabs_list = list(tab_map.keys()) + ["Simulator"]
    chosen = st.tabs(tabs_list)

    for i, name in enumerate(tab_map):
        with chosen[i]:
            tab_map[name](scenario)

    # Simulator tab: generate traffic
    with chosen[-1]:
        _render_simulator(scenario)


def _render_simulator(scenario: NetworkScenario) -> None:
    st.header("Simulator")

    st.caption(
        "Generate traffic between two devices and observe packets, protocol events, "
        "and bandwidth results across the rest of the application."
    )

    devs = list(scenario.devices.keys())
    if len(devs) < 2:
        st.info("Add at least two devices in the Scenario Builder before simulating.")
        return

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        src = st.selectbox("Source", devs, key="sim_src")
    with col2:
        dst_opts = [d for d in devs if d != src]
        dst = st.selectbox("Destination", dst_opts, key="sim_dst")
    with col3:
        proto = st.selectbox("Protocol", ["tcp", "udp", "icmp"], key="sim_proto")
    with col4:
        size = st.number_input("Payload size (bytes)", min_value=16, max_value=1500, value=1024, key="sim_size")

    col5, col6, col7 = st.columns(3)
    with col5:
        count = st.number_input("Packets", min_value=1, max_value=100, value=1, key="sim_count")
    with col6:
        hop_delay = st.number_input("Hop delay (s)", min_value=0.001, max_value=1.0, value=0.01, key="sim_hop")
    with col7:
        link_rate = st.number_input("Link rate (bps)", min_value=1e3, max_value=1e9, value=1_000_000.0, key="sim_rate")

    if st.button("Run simulation", key="sim_run"):
        try:
            scenario.clear()
            flow = TrafficFlow(
                source=src,
                destination=dst,
                protocol=proto,
                size_bytes=size,
                count=count,
                start_time=0.0,
                inter_packet_gap=0.05,
            )
            cfg = SimulationConfig(
                hop_delay=hop_delay,
                processing_delay=0.002,
                link_rate_bps=link_rate,
            )
            result = simulate_flow(scenario, flow, cfg)
            st.session_state["last_result"] = result
            st.success(f"Simulation complete: {len(scenario.packets)} packet(s), {len(scenario.protocol_events)} protocol events.")
            st.rerun()
        except ValueError as e:
            st.error(str(e))

    # Show last result quick view
    if "last_result" in st.session_state:
        r = st.session_state["last_result"]
        st.divider()
        st.subheader("Last simulation result")
        st.metric("Transit time", f"{r.transit_time:.4f} s")
        st.metric("Bandwidth", f"{r.bandwidth_bps:.0f} bps")
        st.metric("Bytes transferred", r.bytes_transferred)
        st.metric("Packets in scenario", len(scenario.packets))
        st.metric("Protocol events", len(scenario.protocol_events))


if __name__ == "__main__":
    main()
