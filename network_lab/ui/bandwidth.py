"""Bandwidth UI component.

Shows simulated bandwidth metrics and chart, plus an optional real
network interface monitor (separate from simulation).
"""
from __future__ import annotations

from typing import Any, Dict, List

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from network_lab.core.protocols import Packet, SimulationResult
from network_lab.modules.bandwidth.analyzer import (
    bandwidth_summary,
    bandwidth_time_series,
    flow_bandwidth,
    flow_transit_time,
    flow_throughput_bytes,
    aggregate_bandwidth,
    total_bytes_transferred,
)
from network_lab.modules.bandwidth.monitor import get_interfaces, live_bandwidth


def render_bandwidth(scenario) -> None:
    st.header("Bandwidth")

    packets = scenario.packets or []
    results = scenario.simulation_results or []

    st.subheader("Simulated traffic bandwidth")
    if not packets:
        st.info("No simulated traffic yet. Run a simulation first.")
    else:
        _render_simulated_bandwidth(packets, results)

    st.divider()
    st.subheader("Real network interface monitoring")
    st.caption("This reads your actual host network interfaces and is separate from the simulation.")
    _render_real_monitoring()


def _render_simulated_bandwidth(packets: List[Packet], results: List[SimulationResult]) -> None:
    summary = bandwidth_summary(packets, results)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total packets", summary["total_packets"])
    c2.metric("Total bytes", summary["total_bytes"])
    c3.metric("Avg bandwidth", f"{summary['avg_bandwidth_bps']:.0f} bps")
    c4.metric("Peak bandwidth", f"{summary['peak_bandwidth_bps']:.0f} bps")

    st.divider()
    ts = summary["time_series"]
    if ts:
        _render_bandwidth_chart(ts)
    else:
        st.info("Not enough data to plot bandwidth over time.")

    if results:
        st.divider()
        st.subheader("Per-flow results")
        for r in results:
            _render_flow_result(r)


def _render_bandwidth_chart(ts: List[Dict[str, Any]]) -> None:
    df = [[d["time"], d["instantaneous_bps"], d["packet_id"], d["cumulative_bytes"]] for d in ts]
    df = {"time": [r[0] for r in df],
           "instantaneous_bps": [r[1] for r in df],
           "packet_id": [r[2] for r in df],
           "cumulative_bytes": [r[3] for r in df]}

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["time"], y=df["instantaneous_bps"],
        mode="lines+markers", name="Instantaneous (bps)",
        line=dict(color="royalblue"),
    ))
    fig.update_layout(
        title="Simulated Bandwidth Over Time",
        xaxis_title="Time (s)",
        yaxis_title="Bandwidth (bps)",
        hovermode="x unified",
        margin=dict(l=20, r=20, t=40, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Cumulative bytes secondary
    fig2 = px.line(
        x=df["time"], y=df["cumulative_bytes"],
        labels={"x": "Time (s)", "y": "Cumulative bytes"},
        title="Cumulative data transferred",
    )
    fig2.update_traces(line_color="darkorange")
    st.plotly_chart(fig2, use_container_width=True)


def _render_flow_result(r: SimulationResult) -> None:
    st.markdown(f"**Flow result**")
    st.metric("Transit time", f"{flow_transit_time(r):.4f} s")
    st.metric("Bandwidth", f"{flow_bandwidth(r):.0f} bps")
    st.metric("Bytes transferred", flow_throughput_bytes(r))
    if r.error_detected:
        st.warning(f"Error detected: {r.error_type}")


def _render_real_monitoring() -> None:
    interfaces = get_interfaces()
    if not interfaces:
        st.warning("psutil not available or no interfaces found.")
        return

    iface = st.selectbox("Interface", interfaces, key="bw_real_iface")
    duration = st.number_input("Measurement window (s)", min_value=0.5, max_value=10.0, value=1.0, key="bw_real_duration")

    if st.button("Measure live bandwidth", key="bw_real_measure"):
        result = live_bandwidth(iface, duration)
        _render_live_result(result)


def _render_live_result(result: Dict[str, Any]) -> None:
    if "error" in result:
        st.error(result["error"])
        return
    c1, c2, c3 = st.columns(3)
    c1.metric("Interface", result["interface"])
    c2.metric("Send", f"{result['send_bps']:.0f} bps")
    c3.metric("Receive", f"{result['recv_bps']:.0f} bps")
    st.metric("Total", f"{result['total_bps']:.0f} bps")
    st.markdown(f"**Duration:** {result['duration_seconds']} s | **Sent:** {result['bytes_sent']} B | **Recv:** {result['bytes_recv']} B")
