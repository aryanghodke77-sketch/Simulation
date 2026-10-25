"""UDP protocol events.

UDP is connectionless, so the protocol engine emits a single DATA-style event
per packet with no handshake.
"""
from __future__ import annotations

from typing import List, Optional

from network_lab.core.protocols import ProtocolEvent


def udp_events(
    source: str,
    destination: str,
    packet_id: int,
    base_time: float = 0.0,
    src_port: Optional[int] = None,
    dst_port: Optional[int] = None,
    payload_size: int = 0,
) -> List[ProtocolEvent]:
    """Generate a single UDP transaction event."""
    return [
        ProtocolEvent(
            timestamp=base_time, source=source, destination=destination,
            protocol="udp", event_type="DATA", packet_id=packet_id,
            direction="out", payload_size=payload_size,
            notes=f"UDP datagram ({payload_size} bytes)",
            src_port=src_port, dst_port=dst_port,
        )
    ]
