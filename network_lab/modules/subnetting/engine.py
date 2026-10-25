"""Subnetting engine.

Operates on CIDR networks and produces teaching-friendly subnet information.
Integrates with the scenario by assigning per-interface IPs.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import ipaddress

from network_lab.core.models import NetworkScenario


def subnet_info(cidr: str) -> Dict[str, Any]:
    """Return detailed subnet information for a CIDR notation string."""
    net = ipaddress.ip_network(cidr, strict=False)
    info: Dict[str, Any] = {
        "cidr": str(net),
        "network_address": str(net.network_address),
        "broadcast_address": str(net.broadcast_address),
        "prefix_length": net.prefixlen,
        "netmask": str(net.netmask),
        "wildcard": str(net.hostmask),
        "total_addresses": net.num_addresses,
        "available_hosts": max(0, net.num_addresses - 2),
        "first_host": str(net.network_address + 1) if net.num_addresses > 2 else None,
        "last_host": str(net.broadcast_address - 1) if net.num_addresses > 2 else None,
        "is_private": net.is_private,
        "is_loopback": net.is_loopback,
        "is_link_local": net.is_link_local,
    }
    return info


def assign_subnet(scenario: NetworkScenario, cidr: str, description: str = "") -> Dict[str, Any]:
    """Record a subnet in the scenario and return its info."""
    info = subnet_info(cidr)
    scenario.subnets[cidr] = description or f"Subnet {cidr}"
    return info


def assignable_hosts(cidr: str) -> List[str]:
    """List usable host IPs in a subnet (excludes network and broadcast)."""
    net = ipaddress.ip_network(cidr, strict=False)
    if net.num_addresses <= 2:
        return []
    return [str(net.network_address + i) for i in range(1, net.num_addresses - 1)]


def subnet_for_ip(ip: str) -> Optional[str]:
    """Return the /24 subnet containing an IP, or None if invalid."""
    try:
        addr = ipaddress.ip_address(ip)
        net = ipaddress.ip_network(f"{addr}/24", strict=False)
        return str(net)
    except ValueError:
        return None


def suggest_ip(scenario: NetworkScenario, device: str, subnet_cidr: str) -> Optional[str]:
    """Suggest an assignable IP for a device within a subnet, avoiding common .1/.254."""
    existing = [
        (iface.ip for iface in scenario.devices[device].interfaces.values() if iface.ip)
    ]
    existing_set = set()
    for gen in existing:
        for ip in gen:
            existing_set.add(ip)
    hosts = assignable_hosts(subnet_cidr)
    for h in hosts:
        if h not in existing_set and not h.endswith(".1") and not h.endswith(".254"):
            return h
    return hosts[0] if hosts else None
