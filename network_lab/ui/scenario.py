"""Scenario Builder UI component.

Allows the user to create and modify the network scenario: add devices,
connect them, assign IP addresses, and define subnets.
"""
from __future__ import annotations

import streamlit as st

from network_lab.core.models import NetworkScenario
from network_lab.core.validators import valid_device_name
from network_lab.core.validators import (
    valid_device_name,
    valid_ip,
    valid_cidr,
    valid_device_name_in_scenario,
    valid_endpoint_pair,
)


def render_scenario_builder(scenario: NetworkScenario) -> None:
    st.header("Scenario Builder")

    tab_add, tab_connect, tab_ip, tab_subnet, tab_info, tab_save_load = st.tabs([
        "Add / Remove Devices",
        "Connect Devices",
        "Assign IPs",
        "Subnets",
        "Scenario Info",
        "Save / Load",
    ])

    with tab_add:
        _render_add_remove(scenario)

    with tab_connect:
        _render_connect(scenario)

    with tab_ip:
        _render_assign_ip(scenario)

    with tab_subnet:
        _render_subnets(scenario)

    with tab_info:
        _render_scenario_info(scenario)

    with tab_save_load:
        _render_save_load(scenario)


def _render_add_remove(scenario: NetworkScenario) -> None:
    st.subheader("Add a device")
    name = st.text_input("Device name", key="sb_device_name")
    kind = st.selectbox("Device type", ["pc", "router", "switch"], key="sb_device_kind")
    ip = st.text_input("IP address (optional)", key="sb_device_ip")

    if st.button("Add device", key="sb_add_device"):
        try:
            valid_device_name(name)
            if name in scenario.devices:
                st.error(f"A device named '{name}' already exists.")
            else:
                valid_ip(ip)  # may raise
                scenario.add_device(name, kind=kind, ip=(valid_ip(ip) or None))
                st.success(f"Added {kind} '{name}'.")
                st.rerun()
        except ValueError as e:
            st.error(str(e))

    st.subheader("Remove a device")
    if scenario.devices:
        remove_name = st.selectbox(
            "Select device to remove", list(scenario.devices.keys()),
            key="sb_remove_device",
        )
        if st.button("Remove device", key="sb_remove_btn"):
            try:
                scenario.remove_device(remove_name)
                st.success(f"Removed '{remove_name}'.")
                st.rerun()
            except ValueError as e:
                st.error(str(e))


def _render_connect(scenario: NetworkScenario) -> None:
    st.subheader("Connect two devices")
    devs = list(scenario.devices.keys())
    if len(devs) < 2:
        st.info("Add at least two devices before connecting.")
        return

    col1, col2 = st.columns(2)
    with col1:
        a = st.selectbox("From", devs, key="sb_connect_a")
    with col2:
        b = st.selectbox("To", [d for d in devs if d != a], key="sb_connect_b")

    if st.button("Connect", key="sb_connect_btn"):
        try:
            valid_endpoint_pair(scenario, a, b)
            scenario.connect(a, b)
            st.success(f"Connected {a} ↔ {b}.")
            st.rerun()
        except ValueError as e:
            st.error(str(e))

    st.subheader("Existing links")
    if scenario.links:
        for link in scenario.links:
            st.markdown(f"`{link.a}:{link.a_iface}`  <->  `{link.b}:{link.b_iface}`")
    else:
        st.markdown("*No links yet.*")

    st.subheader("Remove a link")
    if scenario.links:
        link_names = [f"{l.a} ↔ {l.b}" for l in scenario.links]
        choice = st.selectbox("Select link to remove", link_names, key="sb_disconnect")
        if st.button("Remove link", key="sb_disconnect_btn"):
            a_b = choice.split(" ↔ ")
            scenario.disconnect(a_b[0], a_b[1])
            st.success("Link removed.")
            st.rerun()


def _render_assign_ip(scenario: NetworkScenario) -> None:
    st.subheader("Assign IP address to an interface")
    devs = list(scenario.devices.keys())
    if not devs:
        st.info("Add devices first.")
        return

    device = st.selectbox("Device", devs, key="sb_ip_device")
    dev = scenario.devices[device]
    iface_options = list(dev.interfaces.keys())
    iface = st.selectbox("Interface", iface_options, key="sb_ip_iface")
    ip = st.text_input("IP address", key="sb_ip_value")

    if st.button("Assign IP", key="sb_ip_assign"):
        try:
            valid_ip(ip)
            scenario.assign_ip(device, iface, valid_ip(ip))
            st.success(f"Assigned {valid_ip(ip)} to {device}:{iface}.")
            st.rerun()
        except ValueError as e:
            st.error(str(e))

    st.subheader("Current interface addresses")
    for dname, devobj in scenario.devices.items():
        for iname, iface in devobj.interfaces.items():
            st.markdown(f"`{dname}:{iname}` → {iface.ip or 'unassigned'}")


def _render_subnets(scenario: NetworkScenario) -> None:
    st.subheader("Define a subnet")
    cidr = st.text_input("Subnet (CIDR)", key="sb_subnet_cidr")
    desc = st.text_input("Description (optional)", key="sb_subnet_desc")

    if st.button("Add subnet", key="sb_subnet_add"):
        try:
            valid_cidr(cidr)
            scenario.subnets[cidr] = desc or f"Subnet {cidr}"
            st.success(f"Added subnet {cidr}.")
            st.rerun()
        except ValueError as e:
            st.error(str(e))


def _render_scenario_info(scenario: NetworkScenario) -> None:
    st.subheader("Scenario summary")
    st.json(scenario.summary())


def _render_save_load(scenario: NetworkScenario) -> None:
    import network_lab.storage.database as db
    db.init_db()

    st.subheader("Save current scenario")
    save_name = st.text_input("Scenario name", key="sl_save_name", value=scenario.name)
    if st.button("Save to database", key="sl_save_btn"):
        try:
            valid_device_name(save_name)
            row_id = db.save_scenario(save_name, scenario.to_dict())
            st.success(f"Saved scenario '{save_name}' (id={row_id}).")
            st.rerun()
        except ValueError as e:
            st.error(str(e))
        except Exception as e:
            st.error(f"Could not save: {e}")

    st.subheader("Load a saved scenario")
    saved = db.list_scenarios()
    if not saved:
        st.info("No saved scenarios found.")
        return
    options = [f"{r['name']} (id={r['id']})" for r in saved]
    chosen = st.selectbox("Choose a scenario to load", options, key="sl_load_choice")
    if st.button("Load selected scenario", key="sl_load_btn"):
        row = saved[options.index(chosen)]
        try:
            restored = NetworkScenario.from_dict(row["data"])
            scenario.name = restored.name
            scenario.devices.clear()
            scenario.links.clear()
            scenario.subnets.clear()
            scenario.metadata.clear()
            for dname, dev in restored.devices.items():
                scenario.devices[dname] = dev
            scenario.links.extend(restored.links)
            scenario.subnets.update(restored.subnets)
            scenario.metadata.update(restored.metadata)
            st.success(f"Loaded scenario '{restored.name}'.")
            st.rerun()
        except Exception as e:
            st.error(f"Could not load: {e}")

    st.subheader("Defined subnets")
    if scenario.subnets:
        for cidr, desc in scenario.subnets.items():
            st.markdown(f"**{cidr}** — {desc}")
    else:
        st.markdown("*No subnets defined.*")

    st.subheader("Subnet details")
    detail_cidr = st.text_input("Show details for CIDR", key="sb_subnet_detail")
    if st.button("Show details", key="sb_subnet_detail_btn"):
        try:
            from network_lab.modules.subnetting.engine import subnet_info
            info = subnet_info(valid_cidr(detail_cidr))
            st.json(info)
        except ValueError as e:
            st.error(str(e))
