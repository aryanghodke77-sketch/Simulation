"""Packet analysis for the UI.

Consumes packets from the scenario and produces structured detail views
suitable for the Packet Analysis section of the dashboard.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from network_lab.core.protocols import Packet


def analyze_packet(packet: Packet) -> Dict[str, Any]:
    """Return a structured analysis of a single packet for display."""
    h = packet.headers or {}
    eth = h.get("eth", {})
    ip = h.get("ip", {})

    return {
        "id": packet.id,
        "timestamp": packet.timestamp,
        "source": packet.source,
        "destination": packet.destination,
        "protocol": packet.protocol.upper(),
        "size_bytes": packet.size,
        "ttl": packet.ttl,
        "path": packet.path,
        "path_devices": ", ".join(packet.path),
        "transit_time": packet.transit_time(),
        "headers": {
            "Ethernet": {
                "src_mac": eth.get("src"),
                "dst_mac": eth.get("dst"),
            },
            "IP": {
                "src_ip": ip.get("src"),
                "dst_ip": ip.get("dst"),
                "ttl": ip.get("ttl"),
            },
            "TCP": {
                "src_port": packet.src_port,
                "dst_port": packet.dst_port,
                "flags": {k: v for k, v in (packet.flags or {}).items()},
            } if packet.protocol.lower() == "tcp" else None,
        },
        "flags": packet.flags or {},
        "journey": packet.journey or [],
        "hop_count": len(packet.path) - 1 if packet.path else 0,
    }


def analyze_packets(packets: List[Packet]) -> List[Dict[str, Any]]:
    return [analyze_packet(p) for p in packets]


def packet_table_rows(packets: List[Packet]) -> List[Dict[str, Any]]:
    """Compact rows for a Streamlit dataframe/table view."""
    rows: List[Dict[str, Any]] = []
    for p in packets:
        rows.append({
            "ID": p.id,
            "Time (s)": round(p.timestamp, 4),
            "Source": p.source,
            "Destination": p.destination,
            "Protocol": p.protocol.upper(),
            "Size (bytes)": p.size,
            "TTL": p.ttl,
            "Src Port": p.src_port,
            "Dst Port": p.dst_port,
            "Path": " -> ".join(p.path),
            "Hops": len(p.path) - 1 if p.path else 0,
            "Transit (s)": round(p.transit_time(), 4) if p.transit_time() is not None else None,
        })
    return rows
