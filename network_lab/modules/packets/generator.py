"""Packet generation helpers for the UI layer.

These wrap the simulation engine with a friendlier API for the Streamlit app.
"""
from __future__ import annotations

from typing import Optional

from network_lab.core.models import NetworkScenario
from network_lab.core.protocols import Packet
from network_lab.simulation.network import generate_packet, simulate_flow
from network_lab.simulation.traffic import SimulationConfig, TrafficFlow


def create_packet(
    scenario: NetworkScenario,
    source: str,
    destination: str,
    protocol: str = "tcp",
    size_bytes: int = 1024,
    src_port: Optional[int] = None,
    dst_port: Optional[int] = None,
    config: Optional[SimulationConfig] = None,
) -> Packet:
    """Generate a single packet and add it to the scenario."""
    flow = TrafficFlow(
        source=source,
        destination=destination,
        protocol=protocol,
        size_bytes=size_bytes,
        src_port=src_port,
        dst_port=dst_port,
        count=1,
        start_time=0.0,
    )
    return generate_packet(scenario, flow, packet_index=0, config=config)


def run_simulation(
    scenario: NetworkScenario,
    source: str,
    destination: str,
    protocol: str = "tcp",
    size_bytes: int = 1024,
    count: int = 1,
    config: Optional[SimulationConfig] = None,
):
    """Run a traffic flow and return the SimulationResult."""
    flow = TrafficFlow(
        source=source,
        destination=destination,
        protocol=protocol,
        size_bytes=size_bytes,
        count=count,
        start_time=0.0,
        inter_packet_gap=0.05,
    )
    return simulate_flow(scenario, flow, config=config)
