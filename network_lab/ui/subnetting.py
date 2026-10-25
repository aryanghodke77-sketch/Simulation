"""Subnetting UI component.

Displays subnet information and allows IP assignment suggestions based
on the selected subnet.
"""
from __future__ import annotations

import streamlit as st

from network_lab.core.models import NetworkScenario
from network_lab.modules.subnetting.engine import (
    subnet_info,
    assignable_hosts,
    suggest_ip,
)


def render_subnetting(scenario: NetworkScenario) -> None:
    st.header("Subnetting")

    cidr = st.text_input("Subnet (CIDR)", key="subnet_cidr_input")

    if st.button("Lookup subnet", key="subnet_lookup"):
        try:
            info = subnet_info(cidr)
            _render_subnet_info(info)
        except ValueError as e:
            st.error(str(e))

    st.divider()
    st.subheader("Assignable hosts")
    if cidr:
        try:
            hosts = assignable_hosts(cidr)
            if hosts:
                st.write(f"Usable hosts in {cidr}: {len(hosts)}")
                st.text_area(
                    "Host list (one per line)",
                    "\n".join(hosts[:200]),
                    key="subnet_host_list",
                )
            else:
                st.info("No assignable hosts in this subnet.")
        except ValueError as e:
            st.error(str(e))

    st.divider()
    st.subheader("Suggest IP for a device")
    if scenario.devices:
        device = st.selectbox("Device", list(scenario.devices.keys()), key="subnet_suggest_device")
        if cidr:
            try:
                sug = suggest_ip(scenario, device, cidr)
                if sug:
                    st.success(f"Suggested IP for {device} in {cidr}: `{sug}`")
                else:
                    st.info("No suitable IP could be suggested.")
            except ValueError as e:
                st.error(str(e))


def _render_subnet_info(info: dict) -> None:
    c1, c2, c3 = st.columns(3)
    c1.metric("Network", info["network_address"])
    c2.metric("Broadcast", info["broadcast_address"])
    c3.metric("Prefix", info["prefix_length"])

    st.markdown(f"**Netmask:** `{info['netmask']}`  |  **Wildcard:** `{info['wildcard']}`")
    st.markdown(f"**Total addresses:** {info['total_addresses']}  |  **Available hosts:** {info['available_hosts']}")
    st.markdown(f"**First host:** `{info['first_host']}`  |  **Last host:** `{info['last_host']}`")

    tags = []
    if info["is_private"]:
        tags.append("private")
    if info["is_loopback"]:
        tags.append("loopback")
    if info["is_link_local"]:
        tags.append("link-local")
    if tags:
        st.markdown("**Type:** " + ", ".join(tags))
