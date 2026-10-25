"""Protocol engine orchestrator.

Dispatches to the TCP or UDP event generators based on the packet/protocol,
and merges event streams for visualization.
"""
from __future__ import annotations

from typing import List, Optional

from network_lab.core.protocols import Packet, ProtocolEvent
from network_lab.modules.protocols.tcp import tcp_handshake_events, tcp_teardown_events, tcp_event_summary
from network_lab.modules.protocols.udp import udp_events


def protocol_events_for_packet(
    packet: Packet,
    base_time: Optional[float] = None,
) -> List[ProtocolEvent]:
    """Generate protocol events for a single packet based on its protocol field."""
    base = base_time if base_time is not None else packet.timestamp

    if packet.protocol.lower() == "tcp":
        return tcp_handshake_events(
            source=packet.source,
            destination=packet.destination,
            packet_id=packet.id,
            base_time=base,
            src_port=packet.src_port,
            dst_port=packet.dst_port,
            payload_size=packet.size,
        )
    if packet.protocol.lower() == "udp":
        return udp_events(
            source=packet.source,
            destination=packet.destination,
            packet_id=packet.id,
            base_time=base,
            src_port=packet.src_port,
            dst_port=packet.dst_port,
            payload_size=packet.size,
        )
    # fallback: generic DATA event
    return [
        ProtocolEvent(
            timestamp=base, source=packet.source, destination=packet.destination,
            protocol=packet.protocol, event_type="DATA", packet_id=packet.id,
            direction="out", payload_size=packet.size,
            notes=f"{packet.protocol.upper()} transfer ({packet.size} bytes)",
        )
    ]


def inject_protocol_events(
    scenario,
    packets,
    base_time_fn=None,
) -> List[ProtocolEvent]:
    """Generate and attach protocol events for a list of packets into the scenario."""
    all_events: List[ProtocolEvent] = []
    for p in packets:
        events = protocol_events_for_packet(p, base_time=(base_time_fn(p) if base_time_fn else None))
        for e in events:
            scenario.protocol_events.append(e)
            all_events.append(e)
    return all_events
