"""Packet Analysis UI component.

Displays the packet list, selected packet details, and header breakdown.
"""
from __future__ import annotations

import streamlit as st

from network_lab.core.protocols import Packet
from network_lab.modules.packets.analyzer import analyze_packet, packet_table_rows
from network_lab.modules.packets.parser import parse_headers


def render_packet_analysis(scenario) -> None:
    st.header("Packet Analysis")

    packets = scenario.packets or []
    if not packets:
        st.info("No packets yet. Generate traffic in the simulator section.")
        return

    # Packet list table
    rows = packet_table_rows(packets)
    st.subheader("Packets")
    st.dataframe(rows, use_container_width=True, hide_index=True)

    # Selected packet detail
    selected_id = st.selectbox(
        "Select a packet to inspect",
        [p.id for p in packets],
        key="pa_selected_packet",
    )
    pkt = next((p for p in packets if p.id == selected_id), None)
    if pkt is None:
        return

    st.divider()
    st.subheader(f"Packet #{pkt.id} details")
    analysis = analyze_packet(pkt)
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Source", pkt.source)
    col2.metric("Destination", pkt.destination)
    col3.metric("Protocol", pkt.protocol.upper())
    col4.metric("Size", f"{pkt.size} bytes")

    st.markdown(f"**Timestamp:** {pkt.timestamp:.4f} s")
    st.markdown(f"**TTL:** {pkt.ttl}")
    st.markdown(f"**Path:** " + " → ".join(pkt.path))
    st.markdown(f"**Hops:** {analysis['hop_count']}")
    tt = analysis["transit_time"]
    st.markdown(f"**Transit time:** {tt:.4f} s" if tt is not None else "**Transit time:** N/A")

    st.divider()
    st.subheader("Header breakdown")
    headers = parse_headers(pkt)
    _render_headers(headers)

    st.divider()
    st.subheader("Flags")
    if pkt.flags:
        for k, v in pkt.flags.items():
            st.checkbox(k, value=v, disabled=True, key=f"flag_{pkt.id}_{k}")
    else:
        st.markdown("*No flags.*")

    st.divider()
    st.subheader("Journey (per-hop)")
    if pkt.journey:
        for hop in pkt.journey:
            st.markdown(
                f"Hop {hop['hop']}: `{hop['device']}:{hop['interface']}` @ {hop['time']:.4f}s  "
                f"({hop['event']})"
            )
    else:
        st.markdown("*No journey recorded.*")


def _render_headers(headers: dict) -> None:
    for layer, fields in headers.items():
        if not fields:
            continue
        with st.expander(f"{layer} header"):
            for k, v in fields.items():
                if v is None:
                    st.markdown(f"- **{k}:** _none_")
                elif isinstance(v, dict):
                    st.markdown(f"- **{k}:**")
                    for vk, vv in v.items():
                        st.markdown(f"    - {vk}: {vv}")
                else:
                    st.markdown(f"- **{k}:** `{v}`")
