"""Tests for packet generation and simulation flow."""
from __future__ import annotations

from network_lab.core import default_scenario, Packet, ProtocolEvent
from network_lab.simulation.network import simulate_flow, generate_packet
from network_lab.simulation.traffic import TrafficFlow, SimulationConfig


def test_generate_packet_includes_path():
    s = default_scenario()
    flow = TrafficFlow(source="PC1", destination="PC2", protocol="tcp", size_bytes=1024)
    pkt = generate_packet(s, flow)
    assert pkt.source == "PC1"
    assert pkt.destination == "PC2"
    assert pkt.path == ["PC1", "Router", "PC2"]


def test_generate_packet_header_skeleton():
    s = default_scenario()
    flow = TrafficFlow(source="PC1", destination="PC2", protocol="tcp", size_bytes=1024, src_port=12345, dst_port=80)
    pkt = generate_packet(s, flow)
    assert pkt.headers["eth"]["src"] is not None
    assert pkt.headers["ip"]["src"] is not None
    assert pkt.src_port == 12345
    assert pkt.dst_port == 80


def test_simulate_flow_produces_packets_and_events():
    s = default_scenario()
    flow = TrafficFlow(source="PC1", destination="PC2", protocol="tcp", size_bytes=1024, count=1)
    cfg = SimulationConfig(hop_delay=0.01, processing_delay=0.002, link_rate_bps=1_000_000.0)
    result = simulate_flow(s, flow, cfg)
    assert len(s.packets) == 1
    assert len(s.protocol_events) >= 4  # SYN SYN-ACK ACK DATA
    assert result.bytes_transferred == 1024


def test_simulate_flow_transit_time_positive():
    s = default_scenario()
    flow = TrafficFlow(source="PC1", destination="PC2", protocol="tcp", size_bytes=1024, count=1)
    cfg = SimulationConfig(hop_delay=0.01, processing_delay=0.002, link_rate_bps=1_000_000.0)
    result = simulate_flow(s, flow, cfg)
    assert result.transit_time > 0


def test_simulate_flow_bandwidth_positive():
    s = default_scenario()
    flow = TrafficFlow(source="PC1", destination="PC2", protocol="tcp", size_bytes=1024, count=1)
    cfg = SimulationConfig(hop_delay=0.01, processing_delay=0.002, link_rate_bps=1_000_000.0)
    result = simulate_flow(s, flow, cfg)
    assert result.bandwidth_bps > 0


def test_multipacket_flow():
    s = default_scenario()
    flow = TrafficFlow(source="PC1", destination="PC2", protocol="tcp", size_bytes=500, count=3,
                       inter_packet_gap=0.1)
    cfg = SimulationConfig(hop_delay=0.01, processing_delay=0.002, link_rate_bps=1_000_000.0)
    result = simulate_flow(s, flow, cfg)
    assert len(s.packets) == 3
    assert result.bytes_transferred == 1500
    assert result.transit_time > 0


def test_packet_journey_recorded():
    s = default_scenario()
    flow = TrafficFlow(source="PC1", destination="PC2", protocol="tcp", size_bytes=1024, count=1)
    cfg = SimulationConfig(hop_delay=0.01, processing_delay=0.002, link_rate_bps=1_000_000.0)
    simulate_flow(s, flow, cfg)
    pkt = s.packets[0]
    assert len(pkt.journey) > 0
    for hop in pkt.journey:
        assert "device" in hop
        assert "interface" in hop
        assert "time" in hop
        assert "event" in hop


def test_packet_path_with_iface_populated():
    s = default_scenario()
    flow = TrafficFlow(source="PC1", destination="PC2", protocol="tcp", size_bytes=1024, count=1)
    cfg = SimulationConfig(hop_delay=0.01, processing_delay=0.002, link_rate_bps=1_000_000.0)
    simulate_flow(s, flow, cfg)
    pkt = s.packets[0]
    assert len(pkt.path_with_iface) > 0
    assert all(isinstance(x, tuple) and len(x) == 2 for x in pkt.path_with_iface)
