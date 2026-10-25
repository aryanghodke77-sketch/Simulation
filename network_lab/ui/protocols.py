"""Protocol Visualization UI component.

Step-by-step visualization of protocol events (TCP handshake, data transfer).
"""
from __future__ import annotations

import streamlit as st

from network_lab.core.protocols import ProtocolEvent
from network_lab.simulation.events import step_events, sorted_events
from network_lab.modules.protocols.tcp import tcp_event_summary


def render_protocol_visualization(scenario) -> None:
    st.header("Protocol Visualization")

    events = scenario.protocol_events or []
    if not events:
        st.info("No protocol events yet. Run a simulation with a TCP flow.")
        return

    st.subheader("Event log")
    ordered = sorted_events(events)
    rows = [
        {
            "Time (s)": round(e.timestamp, 4),
            "Source": e.source,
            "Destination": e.destination,
            "Protocol": e.protocol.upper(),
            "Event": e.event_type,
            "Direction": "→" if e.direction == "out" else "←",
            "Packet": e.packet_id,
            "Notes": e.notes,
        }
        for e in ordered
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)

    st.divider()

    steps = step_events(events)
    if not steps:
        return

    st.subheader("Step-by-step visualization")
    total_steps = len(steps)
    current = st.session_state.get("protocol_step", 0)
    current = max(0, min(current, total_steps - 1))

    step_idx = st.slider(
        "Step",
        min_value=0,
        max_value=max(1, total_steps - 1),
        value=current,
        key="protocol_step",
    )

    step = steps[step_idx]
    st.markdown(f"**Step {step_idx + 1} of {total_steps}**")
    st.markdown("---")

    # Show the events in this step
    for ev in step:
        _render_protocol_step_event(ev)

    # Summary
    summary = tcp_event_summary(events)
    with st.expander("Protocol summary"):
        st.write(f"Total events: {summary['total_events']}")
        st.write("By type:", summary["by_type"])
        st.write("Protocols:", summary["protocols"])


def _render_protocol_step_event(ev: ProtocolEvent) -> None:
    direction_arrow = "→" if ev.direction == "out" else "←"
    protocol_color = {
        "tcp": "blue",
        "udp": "green",
        "icmp": "orange",
    }.get(ev.protocol, "gray")

    st.markdown(
        f"**[{ev.timestamp:.3f}s] {ev.event_type}** "
        f"({ev.protocol.upper()}) {direction_arrow}"
    )
    st.markdown(
        f"- **Source:** `{ev.source}`  →  **Destination:** `{ev.destination}`\n"
        f"- **Packet ID:** {ev.packet_id}\n"
        f"- **Payload:** {ev.payload_size} bytes\n"
        f"- **Notes:** {ev.notes}"
    )
    st.divider()
