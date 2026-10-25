"""Lightweight packet, protocol event, and simulation result models.

Kept separate from models.py to avoid a forward-reference tangle; NetworkScenario
imports these at runtime only when needed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Packet:
    id: int
    timestamp: float  # simulated time (seconds)
    source: str      # device name
    destination: str # device name
    protocol: str    # 'tcp', 'udp', 'icmp', ...
    size: int        # bytes
    headers: Dict[str, Any] = field(default_factory=dict)
    payload: bytes = field(default_factory=bytes)
    path: List[str] = field(default_factory=list)          # device names in order
    path_with_iface: List[Tuple[str, str]] = field(default_factory=list)  # (device, iface)
    ttl: int = 64
    src_mac: Optional[str] = None
    dst_mac: Optional[str] = None
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    flags: Dict[str, bool] = field(default_factory=dict)   # e.g. {SYN: True, ACK: False}
    journey: List[Dict[str, Any]] = field(default_factory=list)  # per-hop records

    def transit_time(self) -> Optional[float]:
        """Return simulated end-to-end transit time if journey has start and end."""
        if len(self.journey) < 2:
            return None
        start = self.journey[0].get("time")
        end = self.journey[-1].get("time")
        if start is None or end is None:
            return None
        return end - start


@dataclass
class ProtocolEvent:
    timestamp: float
    source: str
    destination: str
    protocol: str
    event_type: str          # e.g. 'SYN', 'SYN-ACK', 'ACK', 'DATA', 'FIN'
    packet_id: int
    direction: str = "out"  # 'out' from source perspective
    payload_size: int = 0
    notes: str = ""
    src_port: Optional[int] = None
    dst_port: Optional[int] = None


@dataclass
class SimulationResult:
    packet: Packet
    events: List[ProtocolEvent]
    start_time: float
    end_time: float
    bandwidth_bps: float = 0.0
    error_detected: bool = False
    error_type: Optional[str] = None
    bytes_transferred: int = 0

    @property
    def transit_time(self) -> float:
        return self.end_time - self.start_time
