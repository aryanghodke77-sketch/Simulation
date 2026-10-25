"""TCP protocol engine.

Produces the classic TCP connection lifecycle events (SYN, SYN-ACK, ACK,
DATA, FIN) as ProtocolEvent objects suitable for stepwise visualization.
"""
from __future__ import annotations

from typing import List, Optional

from network_lab.core.protocols import ProtocolEvent, Packet


def tcp_handshake_events(
    source: str,
    destination: str,
    packet_id: int,
    base_time: float = 0.0,
    src_port: Optional[int] = None,
    dst_port: Optional[int] = None,
    payload_size: int = 0,
) -> List[ProtocolEvent]:
    """Generate the TCP three-way handshake plus optional data event.

    Sequence: SYN -> SYN-ACK -> ACK -> (DATA)
    """
    events: List[ProtocolEvent] = []
    t = base_time

    events.append(ProtocolEvent(
        timestamp=t, source=source, destination=destination,
        protocol="tcp", event_type="SYN", packet_id=packet_id,
        direction="out", payload_size=0,
        notes="Connection request (SYN)",
        src_port=src_port, dst_port=dst_port,
    ))
    t += 0.001
    events.append(ProtocolEvent(
        timestamp=t, source=destination, destination=source,
        protocol="tcp", event_type="SYN-ACK", packet_id=packet_id,
        direction="in", payload_size=0,
        notes="Connection accepted (SYN-ACK)",
    ))
    t += 0.001
    events.append(ProtocolEvent(
        timestamp=t, source=source, destination=destination,
        protocol="tcp", event_type="ACK", packet_id=packet_id,
        direction="out", payload_size=0,
        notes="Handshake complete (ACK)",
    ))
    if payload_size > 0:
        t += 0.001
        events.append(ProtocolEvent(
            timestamp=t, source=source, destination=destination,
            protocol="tcp", event_type="DATA", packet_id=packet_id,
            direction="out", payload_size=payload_size,
            notes=f"Data transfer ({payload_size} bytes)",
            src_port=src_port, dst_port=dst_port,
        ))
    return events


def tcp_teardown_events(
    source: str,
    destination: str,
    packet_id: int,
    base_time: float = 0.0,
) -> List[ProtocolEvent]:
    """Generate TCP connection teardown events (FIN handshake)."""
    events: List[ProtocolEvent] = []
    t = base_time

    events.append(ProtocolEvent(
        timestamp=t, source=source, destination=destination,
        protocol="tcp", event_type="FIN", packet_id=packet_id,
        direction="out", payload_size=0,
        notes="Connection close request (FIN)",
    ))
    t += 0.001
    events.append(ProtocolEvent(
        timestamp=t, source=destination, destination=source,
        protocol="tcp", event_type="ACK", packet_id=packet_id,
        direction="in", payload_size=0,
        notes="Close acknowledged (ACK)",
    ))
    return events


def tcp_event_summary(events: List[ProtocolEvent]) -> dict:
    """Summarize a list of TCP events for display."""
    counts: dict = {}
    for e in events:
        counts[e.event_type] = counts.get(e.event_type, 0) + 1
    return {
        "total_events": len(events),
        "by_type": counts,
        "protocols": sorted({e.protocol for e in events}),
    }
