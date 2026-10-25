"""Network/Traffic Simulator.

Generates packets from a TrafficFlow, moves them through the topology
found by the scenario, and records the journey plus protocol events.
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from network_lab.core.models import NetworkScenario
from network_lab.core.protocols import Packet, ProtocolEvent, SimulationResult
from network_lab.modules.protocols.tcp import tcp_handshake_events
from network_lab.modules.protocols.engine import protocol_events_for_packet
from network_lab.modules.errors.engine import detect_error
from network_lab.simulation.traffic import SimulationConfig, TrafficFlow


def _mac_for(device: str, scenario: NetworkScenario) -> str:
    """Generate a deterministic-ish MAC for display."""
    seed = sum(ord(c) for c in device) % 256
    return f"00:1A:2B:3C:4D:{seed:02X}"


def generate_packet(
    scenario: NetworkScenario,
    flow: TrafficFlow,
    packet_index: int = 0,
    config: Optional[SimulationConfig] = None,
) -> Packet:
    """Create a packet for a flow, including a basic header skeleton."""
    config = config or SimulationConfig()
    ts = flow.start_time + packet_index * flow.inter_packet_gap

    path_names = scenario.find_path_names(flow.source, flow.destination)
    iface_path = scenario.interfaces_on_path(flow.source, flow.destination)

    src_mac = _mac_for(flow.source, scenario)
    # destination MAC is the next-hop MAC; for simplicity we use the next device's MAC
    dst_mac = _mac_for(path_names[1] if len(path_names) > 1 else flow.destination, scenario)

    flags: Dict[str, bool] = {}
    if flow.protocol.lower() == "tcp":
        # default TCP flag skeleton; protocol engine refines per event
        flags = {"SYN": False, "ACK": False, "FIN": False, "RST": False}

    pkt = Packet(
        id=packet_index,
        timestamp=ts,
        source=flow.source,
        destination=flow.destination,
        protocol=flow.protocol,
        size=flow.size_bytes,
        headers={
            "eth": {"src": src_mac, "dst": dst_mac},
            "ip": {
                "src": scenario.device_interface(flow.source, "eth0").ip or "0.0.0.0",
                "dst": scenario.device_interface(flow.destination, "eth0").ip or "0.0.0.0",
                "ttl": 64,
            },
        },
        payload=b"X" * max(0, flow.size_bytes - 54),
        path=list(path_names),
        path_with_iface=list(iface_path),
        src_mac=src_mac,
        dst_mac=dst_mac,
        src_port=flow.src_port,
        dst_port=flow.dst_port,
        flags=flags,
        ttl=64,
    )
    return pkt


def simulate_flow(
    scenario: NetworkScenario,
    flow: TrafficFlow,
    config: Optional[SimulationConfig] = None,
) -> SimulationResult:
    """Run a single traffic flow through the topology.

    Generates packets, moves each through the path, records per-hop journey
    entries and protocol events, and returns a SimulationResult with metrics.
    """
    config = config or SimulationConfig()
    events: List[ProtocolEvent] = []
    start_time = flow.start_time
    end_time = start_time
    bytes_transferred = 0

    for i in range(flow.count):
        pkt = generate_packet(scenario, flow, packet_index=i, config=config)
        scenario.packets.append(pkt)

        # Move packet through the path
        journey: List[Dict[str, object]] = []
        simulated_time = pkt.timestamp

        for hop_index in range(len(pkt.path)):
            device = pkt.path[hop_index]
            iface = pkt.path_with_iface[hop_index][1] if hop_index < len(pkt.path_with_iface) else "eth0"

            hop_entry = {
                "hop": hop_index,
                "device": device,
                "interface": iface,
                "time": simulated_time,
                "event": _hop_event(device, hop_index, len(pkt.path)),
            }
            journey.append(hop_entry)

            # Add protocol events via the protocol engine.
            # TCP handshake/data is generated once per packet, at the first hop.
            if flow.protocol.lower() == "tcp" and hop_index == 0:
                proto_events = tcp_handshake_events(
                    source=flow.source,
                    destination=flow.destination,
                    packet_id=pkt.id,
                    base_time=simulated_time,
                    src_port=flow.src_port,
                    dst_port=flow.dst_port,
                    payload_size=pkt.size,
                )
                for ev in proto_events:
                    scenario.protocol_events.append(ev)
                    events.append(ev)
            elif flow.protocol.lower() in {"udp", "icmp"}:
                # UDP/icmp are connectionless; generate one DATA-style event per packet.
                if hop_index == 0:
                    proto_events = protocol_events_for_packet(pkt, base_time=simulated_time)
                    for ev in proto_events:
                        scenario.protocol_events.append(ev)
                        events.append(ev)

            # advance time: hop delay + processing delay
            simulated_time += config.hop_delay + config.processing_delay

            # transmission time contribution to bandwidth
            simulated_time += pkt.size / config.link_rate_bps

        pkt.journey = journey
        end_time = max(end_time, simulated_time)
        bytes_transferred += pkt.size

        # Run error detection on this packet if configured.
        error_detected = False
        error_type: Optional[str] = None
        if config.error_detection_method:
            inject = (
                (config.error_inject_on_packet is not None and i == config.error_inject_on_packet)
                or (config.error_injection_rate > 0 and (i % max(1, int(1 / max(config.error_injection_rate, 1e-9)))) == 0)
            )
            detection = detect_error(
                pkt.payload,
                method=config.error_detection_method,
                inject_error=inject,
                error_location=(i % 8),
            )
            error_detected = detection["error_detected"]
            error_type = detection["method"] if error_detected else None

        # Record per-packet result (for aggregation).
        # For TCP, events for this packet are the tail of the scenario event list
        # whose packet_id matches this packet; for other protocols, use the engine.
        if flow.protocol.lower() == "tcp":
            pkt_events = [e for e in scenario.protocol_events if e.packet_id == pkt.id]
        elif flow.protocol.lower() in {"udp", "icmp"}:
            pkt_events = protocol_events_for_packet(pkt, base_time=pkt.timestamp)
        else:
            pkt_events = []
        scenario.simulation_results.append(
            SimulationResult(
                packet=pkt,
                events=pkt_events,
                start_time=pkt.timestamp,
                end_time=simulated_time,
                bandwidth_bps=(pkt.size / (simulated_time - pkt.timestamp)) * 8 if simulated_time > pkt.timestamp else 0.0,
                bytes_transferred=pkt.size,
                error_detected=error_detected,
                error_type=error_type,
            )
        )

    # Aggregate result for the whole flow.
    # Only add the aggregate row when the flow actually produced at least one packet,
    # so scenario.simulation_results contains one row per packet plus exactly one
    # flow-level row. This keeps analysis/aggregation semantics clean.
    if flow.count > 0:
        flow_end = end_time
        flow_bw = (bytes_transferred * 8) / (flow_end - start_time) if (flow_end - start_time) > 0 else 0.0

        any_error = any(
            getattr(r, "error_detected", False)
            for r in scenario.simulation_results if r.packet is not None
        )
        error_type: Optional[str] = None
        if any_error:
            for r in scenario.simulation_results:
                if getattr(r, "error_detected", False):
                    error_type = r.error_type
                    break
        scenario.simulation_results.append(
            SimulationResult(
                packet=pkt,
                events=events,
                start_time=start_time,
                end_time=end_time,
                bandwidth_bps=flow_bw,
                bytes_transferred=bytes_transferred,
                error_detected=any_error,
                error_type=error_type,
            )
        )

    return scenario.simulation_results[-1]

    return scenario.simulation_results[-1]

    return scenario.simulation_results[-1]


def _hop_event(device: str, hop_index: int, total_hops: int) -> str:
    if hop_index == 0:
        return "egress"
    if hop_index == total_hops - 1:
        return "ingress"
    return "forward"
