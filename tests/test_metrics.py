"""Tests for analysis metrics and packet inspection."""
from __future__ import annotations

import network_lab
from network_lab.core import default_scenario
from network_lab.simulation.network import simulate_flow
from network_lab.simulation.traffic import TrafficFlow, SimulationConfig
from network_lab.modules.packets.analyzer import analyze_packet, packet_table_rows
from network_lab.modules.packets.parser import parse_headers
from network_lab.modules.bandwidth.analyzer import (
    aggregate_bandwidth,
    bandwidth_summary,
    bandwidth_time_series,
    flow_bandwidth,
    flow_transit_time,
    total_bytes_transferred,
)


def test_analyze_packet_fields():
    s = default_scenario()
    flow = TrafficFlow(source="PC1", destination="PC2", protocol="tcp", size_bytes=1024,
                       src_port=12345, dst_port=80, count=1)
    simulate_flow(s, flow)
    pkt = s.packets[0]
    a = analyze_packet(pkt)
    assert a["source"] == "PC1"
    assert a["destination"] == "PC2"
    assert a["protocol"] == "TCP"
    assert a["size_bytes"] == 1024
    assert a["hop_count"] == 2
    assert a["headers"]["Ethernet"]["src_mac"] is not None
    assert a["headers"]["IP"]["src_ip"] is not None
    assert a["headers"]["TCP"]["src_port"] == 12345


def test_packet_table_rows():
    s = default_scenario()
    flow = TrafficFlow(source="PC1", destination="PC2", protocol="tcp", size_bytes=1024, count=2)
    simulate_flow(s, flow)
    rows = packet_table_rows(s.packets)
    assert len(rows) == 2
    assert rows[0]["Protocol"] == "TCP"
    assert rows[0]["Source"] == "PC1"
    assert rows[0]["Hops"] == 2


def test_parse_headers():
    s = default_scenario()
    flow = TrafficFlow(source="PC1", destination="PC2", protocol="tcp", size_bytes=1024, count=1)
    simulate_flow(s, flow)
    pkt = s.packets[0]
    h = parse_headers(pkt)
    assert "Ethernet" in h
    assert "IP" in h
    assert h["Ethernet"]["src"] is not None
    assert h["IP"]["src"] is not None
    assert h["TCP"]["src_port"] == pkt.src_port


def test_bandwidth_summary():
    s = default_scenario()
    flow = TrafficFlow(source="PC1", destination="PC2", protocol="tcp", size_bytes=1024, count=2)
    cfg = SimulationConfig(hop_delay=0.01, processing_delay=0.002, link_rate_bps=1_000_000.0)
    simulate_flow(s, flow, cfg)
    summary = bandwidth_summary(s.packets, s.simulation_results)
    assert summary["total_packets"] == 2
    assert summary["total_bytes"] == 2048
    assert summary["avg_bandwidth_bps"] > 0
    assert len(summary["time_series"]) == 2


def test_bandwidth_time_series_monotonic():
    s = default_scenario()
    flow = TrafficFlow(source="PC1", destination="PC2", protocol="tcp", size_bytes=500, count=3,
                       inter_packet_gap=0.1)
    simulate_flow(s, flow)
    ts = bandwidth_time_series(s.packets)
    assert len(ts) == 3
    assert ts[0]["cumulative_bytes"] < ts[-1]["cumulative_bytes"]
    assert ts[-1]["cumulative_bytes"] == 1500


def test_aggregate_bandwidth():
    results = []
    for i in range(3):
        r = type("R", (), {"bandwidth_bps": 1000.0 * (i + 1)})()
        results.append(r)
    assert aggregate_bandwidth(results) == 2000.0


def test_total_bytes_transferred():
    from network_lab.core.protocols import SimulationResult
    from network_lab.core import Packet
    results = [
        SimulationResult(packet=Packet(id=0, timestamp=0, source="A", destination="B", protocol="tcp", size=100),
                         events=[], start_time=0, end_time=1, bytes_transferred=100),
        SimulationResult(packet=Packet(id=1, timestamp=0, source="A", destination="B", protocol="tcp", size=200),
                         events=[], start_time=0, end_time=1, bytes_transferred=200),
    ]
    assert total_bytes_transferred(results) == 300


def test_flow_bandwidth_and_transit():
    from network_lab.core.protocols import SimulationResult, Packet
    p = Packet(id=1, timestamp=0.0, source="A", destination="B", protocol="tcp", size=100,
               journey=[{"time": 0.0}, {"time": 0.5}])
    r = SimulationResult(packet=p, events=[], start_time=0.0, end_time=0.5, bandwidth_bps=1600.0, bytes_transferred=100)
    assert flow_bandwidth(r) == 1600.0
    assert flow_transit_time(r) == 0.5
