"""Packet header parser.

Provides structured access to packet headers. For the V0.1 slice this is a
lightweight parser over the headers dict stored on Packet. Where richer
construction/parsing is needed later, Scapy can be used for that purpose.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from network_lab.core.protocols import Packet


def parse_headers(packet: Packet) -> Dict[str, Dict[str, Any]]:
    """Return a typed breakdown of packet headers."""
    h = packet.headers or {}
    return {
        "Ethernet": {
            "src": h.get("eth", {}).get("src"),
            "dst": h.get("eth", {}).get("dst"),
        },
        "IP": {
            "src": h.get("ip", {}).get("src"),
            "dst": h.get("ip", {}).get("dst"),
            "ttl": h.get("ip", {}).get("ttl"),
        },
        "TCP": _parse_tcp(packet),
    }


def _parse_tcp(packet: Packet) -> Optional[Dict[str, Any]]:
    if packet.protocol.lower() != "tcp":
        return None
    return {
        "src_port": packet.src_port,
        "dst_port": packet.dst_port,
        "sequence": packet.headers.get("tcp", {}).get("seq"),
        "acknowledgment": packet.headers.get("tcp", {}).get("ack"),
        "flags": packet.flags or {},
        "window": packet.headers.get("tcp", {}).get("window"),
    }


def parse_mac(mac: Optional[str]) -> Optional[Tuple[int, int, int, int, int, int]]:
    """Parse a MAC string '00:1A:2B:3C:4D:5E' into a tuple of ints, or None."""
    if not mac:
        return None
    try:
        parts = mac.split(":")
        if len(parts) != 6:
            return None
        return tuple(int(p, 16) for p in parts)
    except ValueError:
        return None
