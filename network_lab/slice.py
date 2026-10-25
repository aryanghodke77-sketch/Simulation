"""Vertical slice: the smallest end-to-end network simulation flow.

Scenario -> topology -> one simulated TCP packet -> path traversal ->
protocol events -> basic traffic/bandwidth calculation.

Everything here is produced by executing the underlying simulation model,
not by hardcoding demonstration data.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from network_lab.core.models import NetworkScenario
from network_lab.core.protocols import Packet, ProtocolEvent, SimulationResult
from network_lab.simulation.network import simulate_flow
from network_lab.simulation.traffic import SimulationConfig, TrafficFlow


def build_demo_scenario(name: str = "Lab 1: Simple routed network") -> NetworkScenario:
    """Build the canonical V0.1 demo scenario: PC1 - Router - PC2.

    This is the same scenario used by the Streamlit app's default state.
    """
    s = NetworkScenario(name)
    s.add_device("PC1", "pc")
    s.add_device("Router", "router")
    s.add_device("PC2", "pc")

    # Connect on the interfaces that will carry the IPs, so the topology,
    # addressing, and path traversal are internally consistent.
    s.connect("PC1", "Router", a_iface="eth0", b_iface="eth0")
    s.connect("Router", "PC2", a_iface="eth1", b_iface="eth0")

    s.assign_ip("PC1", "eth0", "192.168.1.10")
    s.assign_ip("Router", "eth0", "192.168.1.1")
    s.assign_ip("Router", "eth1", "192.168.2.1")
    s.assign_ip("PC2", "eth0", "192.168.2.10")

    s.subnets["192.168.1.0/24"] = "LAN A (PC1 side)"
    s.subnets["192.168.2.0/24"] = "LAN B (PC2 side)"
    return s


def run_vertical_slice(
    scenario: Optional[NetworkScenario] = None,
    *,
    source: str = "PC1",
    destination: str = "PC2",
    protocol: str = "tcp",
    size_bytes: int = 1024,
    count: int = 1,
    hop_delay: float = 0.01,
    link_rate_bps: float = 1_000_000.0,
) -> Tuple[NetworkScenario, Dict[str, Any]]:
    """Run the vertical slice and return (scenario, trace).

    The trace is a plain Python dict summarizing what the simulation produced,
    suitable for tests and for inspection outside the UI.
    """
    if scenario is None:
        scenario = build_demo_scenario()

    scenario.clear()
    flow = TrafficFlow(
        source=source,
        destination=destination,
        protocol=protocol,
        size_bytes=size_bytes,
        count=count,
        start_time=0.0,
        inter_packet_gap=0.05,
    )
    cfg = SimulationConfig(
        hop_delay=hop_delay,
        processing_delay=0.002,
        link_rate_bps=link_rate_bps,
    )
    result = simulate_flow(scenario, flow, cfg)

    trace = build_trace(scenario, result)
    return scenario, trace


def build_trace(
    scenario: NetworkScenario,
    result: Optional[SimulationResult] = None,
) -> Dict[str, Any]:
    """Summarize the current scenario state as a plain trace dict."""
    packets = scenario.packets or []
    events = scenario.protocol_events or []
    results = scenario.simulation_results or []

    chosen = result if result is not None else (results[-1] if results else None)

    return {
        "scenario": {
            "name": scenario.name,
            "devices": list(scenario.devices.keys()),
            "links": [f"{l.a}<->{l.b}" for l in scenario.links],
            "subnets": list(scenario.subnets.keys()),
            "packets": len(scenario.packets),
            "protocol_events": len(scenario.protocol_events),
            "simulation_results": len(scenario.simulation_results),
        },
        "path": _path(scenario),
        "packets": _packets_trace(packets),
        "protocol_events": _events_trace(events),
        "simulation_results": _results_trace(results),
        "selected_result": _result_trace(chosen),
    }


def _path(scenario: NetworkScenario) -> List[str]:
    try:
        return scenario.find_path_names("PC1", "PC2")
    except ValueError:
        return []


def _packets_trace(packets: List[Packet]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in packets:
        out.append({
            "id": p.id,
            "timestamp": p.timestamp,
            "source": p.source,
            "destination": p.destination,
            "protocol": p.protocol,
            "size_bytes": p.size,
            "path": list(p.path),
            "path_with_iface": list(p.path_with_iface),
            "journey": list(p.journey),
            "transit_time": p.transit_time(),
        })
    return out


def _events_trace(events: List[ProtocolEvent]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for e in events:
        out.append({
            "timestamp": e.timestamp,
            "source": e.source,
            "destination": e.destination,
            "protocol": e.protocol,
            "event_type": e.event_type,
            "packet_id": e.packet_id,
            "direction": e.direction,
            "payload_size": e.payload_size,
            "notes": e.notes,
        })
    return out


def _results_trace(results: List[SimulationResult]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for r in results:
        out.append({
            "packet_id": r.packet.id if r.packet is not None else None,
            "start_time": r.start_time,
            "end_time": r.end_time,
            "transit_time": r.transit_time,
            "bandwidth_bps": r.bandwidth_bps,
            "bytes_transferred": r.bytes_transferred,
            "error_detected": r.error_detected,
            "error_type": r.error_type,
            "event_count": len(r.events),
        })
    return out


def _result_trace(result: Optional[SimulationResult]) -> Optional[Dict[str, Any]]:
    if result is None:
        return None
    return {
        "packet_id": result.packet.id if result.packet is not None else None,
        "start_time": result.start_time,
        "end_time": result.end_time,
        "transit_time": result.transit_time,
        "bandwidth_bps": result.bandwidth_bps,
        "bytes_transferred": result.bytes_transferred,
        "error_detected": result.error_detected,
        "error_type": result.error_type,
        "event_count": len(result.events),
    }
