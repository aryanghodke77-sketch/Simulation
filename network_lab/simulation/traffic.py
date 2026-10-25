"""Traffic model and flow definitions for the simulator.

A TrafficFlow captures the intent: who sends what, to whom, using which
protocol, over what simulated time window.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TrafficFlow:
    source: str
    destination: str
    protocol: str  # 'tcp', 'udp', 'icmp'
    size_bytes: int
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    count: int = 1  # number of packets to generate for this flow
    start_time: float = 0.0
    inter_packet_gap: float = 0.0  # simulated seconds between packets


@dataclass
class SimulationConfig:
    """Parameters that shape how the simulator behaves."""
    # per-hop delay in simulated seconds
    hop_delay: float = 0.01
    # processing delay at each device (router/PC)
    processing_delay: float = 0.002
    # link transmission rate used for bandwidth calc (bytes/sec)
    link_rate_bps: float = 1_000_000.0
    # error-detection method to apply to each packet payload; one of
    # 'parity', 'checksum', 'crc', or None.
    error_detection_method: Optional[str] = None
    # if > 0, errors are injected on a fraction of packets; for testing,
    # set error_inject_on_packet to force injection on a specific packet index.
    error_injection_rate: float = 0.0
    error_inject_on_packet: Optional[int] = None
    seed: Optional[int] = None
