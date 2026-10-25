"""Input validation for the Network Lab UI.

Keeps validation out of the core models while giving the UI clear,
consistent error messages.
"""
from __future__ import annotations

import ipaddress
import re

from network_lab.core.models import NetworkScenario


def valid_device_name(name: str) -> str:
    name = name.strip()
    if not name:
        raise ValueError("Device name cannot be empty")
    if not re.match(r"^[A-Za-z0-9_]+$", name):
        raise ValueError("Device name may only contain letters, digits, and underscores")
    return name


def valid_ip(ip: str, allow_none: bool = True) -> Optional[str]:
    if allow_none and (ip is None or ip.strip() == ""):
        return None
    ip = ip.strip()
    try:
        ipaddress.ip_address(ip)
    except ValueError as e:
        raise ValueError(f"'{ip}' is not a valid IP address") from e
    return ip


def valid_cidr(cidr: str) -> str:
    cidr = cidr.strip()
    try:
        net = ipaddress.ip_network(cidr, strict=False)
    except ValueError as e:
        raise ValueError(f"'{cidr}' is not a valid CIDR network") from e
    return str(net)


def valid_device_name_in_scenario(scenario: NetworkScenario, name: str) -> str:
    valid_device_name(name)
    if name not in scenario.devices:
        raise ValueError(f"Device '{name}' does not exist in the current scenario")
    return name


def valid_endpoint_pair(scenario: NetworkScenario, a: str, b: str) -> Tuple[str, str]:
    valid_device_name_in_scenario(scenario, a)
    valid_device_name_in_scenario(scenario, b)
    if a == b:
        raise ValueError("Cannot connect a device to itself")
    return a, b


def valid_protocol(protocol: str) -> str:
    p = protocol.strip().lower()
    if p not in {"tcp", "udp", "icmp"}:
        raise ValueError("Protocol must be one of: tcp, udp, icmp")
    return p
