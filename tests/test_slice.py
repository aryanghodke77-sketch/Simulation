"""Correctness-focused integration tests for the V0.1 vertical slice.

These assert *exact* values derived from the simulation formulas and the
default demo topology (PC1:eth0 <-> Router:eth0, Router:eth1 <-> PC2:eth0),
not just "something positive was produced".

Assumptions for the known-config tests:
- Topology: PC1:eth0 - Router:eth0, Router:eth1 - PC2:eth0 (links on the same
  interfaces that carry the assigned IPs).
- Path PC1 -> PC2: PC1, Router, PC2 (3 devices, 2 links).
- interfaces_on_path(PC1, PC2) == [('PC1','eth0'), ('Router','eth0'),
  ('Router','eth1'), ('PC2','eth0')].
- SimulationConfig(hop_delay=0.01, processing_delay=0.002,
  link_rate_bps=1_000_000.0).
- TrafficFlow(source='PC1', destination='PC2', protocol='tcp',
  size_bytes=1024, count=1, start_time=0.0, inter_packet_gap=0.0).
- Packet timestamp = 0.0 (start_time + 0*gap).
- Per-hop simulated-time advance in simulate_flow:
  hop_delay + processing_delay + size/link_rate_bps
  = 0.01 + 0.002 + 1024/1_000_000 = 0.013024 s.
- Path has 3 devices, so the hop loop runs 3 times, advancing from
  0.0 -> 0.013024 -> 0.026048 -> 0.039072.
- result.transit_time = 0.039072; bytes = 1024;
  bandwidth_bps = (1024*8)/0.039072 = 209664.20966420966.
- TCP handshake: tcp_handshake_events base_time=0.0 produces
  SYN@0.0, SYN-ACK@0.001, ACK@0.002, DATA@0.003 with ports on SYN/DATA.
- inject_protocol_events is intentionally *not* called by simulate_flow for
  TCP anymore; the simulator now delegates directly to tcp_handshake_events.
  UDP/icmp use protocol_events_for_packet once per packet at hop 0.
"""
from __future__ import annotations

import pytest

from network_lab.core.protocols import ProtocolEvent
from network_lab.slice import build_demo_scenario, run_vertical_slice
from network_lab.simulation.network import simulate_flow
from network_lab.simulation.traffic import SimulationConfig, TrafficFlow

CFG = SimulationConfig(hop_delay=0.01, processing_delay=0.002, link_rate_bps=1_000_000.0)


class TestDemoTopology:
    def test_devices(self):
        s = build_demo_scenario()
        assert list(s.devices.keys()) == ["PC1", "Router", "PC2"]

    def test_links(self):
        s = build_demo_scenario()
        links = sorted(
            (min(l.a, l.b), max(l.a, l.b), l.a_iface, l.b_iface)
            for l in s.links
        )
        assert len(links) == 2
        assert ("PC1", "Router", "eth0", "eth0") in links
        assert ("PC2", "Router", "eth1", "eth0") in links

    def test_subnets(self):
        s = build_demo_scenario()
        assert s.subnets == {
            "192.168.1.0/24": "LAN A (PC1 side)",
            "192.168.2.0/24": "LAN B (PC2 side)",
        }

    def test_ip_assignment(self):
        s = build_demo_scenario()
        assert s.device_interface("PC1", "eth0").ip == "192.168.1.10"
        assert s.device_interface("Router", "eth0").ip == "192.168.1.1"
        assert s.device_interface("Router", "eth1").ip == "192.168.2.1"
        assert s.device_interface("PC2", "eth0").ip == "192.168.2.10"


class TestPathAndInterfaces:
    def test_path_names(self):
        s = build_demo_scenario()
        assert s.find_path_names("PC1", "PC2") == ["PC1", "Router", "PC2"]

    def test_interfaces_on_path(self):
        s = build_demo_scenario()
        ifaces = s.interfaces_on_path("PC1", "PC2")
        assert ifaces == [
            ("PC1", "eth0"),
            ("Router", "eth0"),
            ("Router", "eth1"),
            ("PC2", "eth0"),
        ]

    def test_packet_path_with_iface(self):
        s = build_demo_scenario()
        flow = TrafficFlow(source="PC1", destination="PC2", protocol="tcp", size_bytes=1024)
        from network_lab.simulation.network import generate_packet
        pkt = generate_packet(s, flow)
        assert pkt.path == ["PC1", "Router", "PC2"]
        assert pkt.path_with_iface == [
            ("PC1", "eth0"),
            ("Router", "eth0"),
            ("Router", "eth1"),
            ("PC2", "eth0"),
        ]

    def test_packet_header_ips(self):
        s = build_demo_scenario()
        flow = TrafficFlow(source="PC1", destination="PC2", protocol="tcp", size_bytes=1024)
        from network_lab.simulation.network import generate_packet
        pkt = generate_packet(s, flow)
        assert pkt.headers["ip"]["src"] == "192.168.1.10"
        assert pkt.headers["ip"]["dst"] == "192.168.2.10"


class TestSinglePacketTcpFlowKnownValues:
    def setup_method(self):
        self.scenario = build_demo_scenario()
        self.scenario.clear()
        self.flow = TrafficFlow(
            source="PC1", destination="PC2", protocol="tcp",
            size_bytes=1024, count=1, start_time=0.0, inter_packet_gap=0.0,
            src_port=12345, dst_port=80,
        )
        self.result = simulate_flow(self.scenario, self.flow, CFG)

    def test_packet_count(self):
        assert len(self.scenario.packets) == 1

    def test_packet_identity(self):
        p = self.scenario.packets[0]
        assert p.source == "PC1"
        assert p.destination == "PC2"
        assert p.protocol == "tcp"
        assert p.size == 1024
        assert p.id == 0
        assert p.timestamp == 0.0
        assert p.src_port == 12345
        assert p.dst_port == 80

    def test_packet_path_exact(self):
        p = self.scenario.packets[0]
        assert p.path == ["PC1", "Router", "PC2"]
        assert p.path_with_iface == [
            ("PC1", "eth0"), ("Router", "eth0"),
            ("Router", "eth1"), ("PC2", "eth0"),
        ]

    def test_journey_devices_and_interfaces(self):
        p = self.scenario.packets[0]
        assert len(p.journey) == 3
        assert [h["device"] for h in p.journey] == ["PC1", "Router", "PC2"]
        assert [h["interface"] for h in p.journey] == ["eth0", "eth0", "eth1"]
        assert [h["event"] for h in p.journey] == ["egress", "forward", "ingress"]
        # timestamps increasing, per-hop advance = 0.013024
        assert p.journey[0]["time"] == pytest.approx(0.0)
        assert p.journey[1]["time"] == pytest.approx(0.013024)
        assert p.journey[2]["time"] == pytest.approx(0.026048)

    def test_journey_times_final(self):
        p = self.scenario.packets[0]
        # end_time after loop = 0.039072
        assert p.journey[-1]["time"] == pytest.approx(0.026048)
        assert self.result.end_time == pytest.approx(0.039072)

    def test_protocol_event_sequence_and_timestamps(self):
        events = self.scenario.protocol_events
        assert len(events) == 4
        expected = [
            ("SYN", 0.0, "out", 12345, 80),
            ("SYN-ACK", 0.001, "in", None, None),
            ("ACK", 0.002, "out", None, None),
            ("DATA", 0.003, "out", 12345, 80),
        ]
        for ev, (etype, ts, direction, sp, dp) in zip(events, expected):
            assert ev.event_type == etype
            assert ev.timestamp == pytest.approx(ts)
            assert ev.direction == direction
            assert ev.src_port == sp
            assert ev.dst_port == dp
            assert ev.packet_id == 0
            assert ev.protocol == "tcp"

    def test_protocol_event_ordering(self):
        events = self.scenario.protocol_events
        timestamps = [e.timestamp for e in events]
        assert timestamps == sorted(timestamps)

    def test_result_known_values(self):
        r = self.result
        assert r.bytes_transferred == 1024
        assert r.transit_time == pytest.approx(0.039072)
        assert r.bandwidth_bps == pytest.approx(209664.20966420966)
        assert r.start_time == 0.0
        assert r.error_detected is False

    def test_result_events_match_packet(self):
        r = self.result
        assert [e.event_type for e in r.events] == ["SYN", "SYN-ACK", "ACK", "DATA"]


class TestMultiPacketTcpFlow:
    def test_packets_and_bytes(self):
        s = build_demo_scenario(); s.clear()
        flow = TrafficFlow(
            source="PC1", destination="PC2", protocol="tcp",
            size_bytes=500, count=3, start_time=0.0, inter_packet_gap=0.1,
        )
        r = simulate_flow(s, flow, CFG)
        assert len(s.packets) == 3
        assert r.bytes_transferred == 1500

    def test_packet_timestamps_from_gap(self):
        s = build_demo_scenario(); s.clear()
        flow = TrafficFlow(
            source="PC1", destination="PC2", protocol="tcp",
            size_bytes=500, count=3, start_time=0.0, inter_packet_gap=0.1,
        )
        simulate_flow(s, flow, CFG)
        assert s.packets[0].timestamp == 0.0
        assert s.packets[1].timestamp == 0.1
        assert s.packets[2].timestamp == 0.2


class TestUdpFlow:
    def test_single_data_event(self):
        s = build_demo_scenario(); s.clear()
        flow = TrafficFlow(
            source="PC1", destination="PC2", protocol="udp",
            size_bytes=500, count=1, start_time=0.0, inter_packet_gap=0.0,
            src_port=12345, dst_port=80,
        )
        r = simulate_flow(s, flow, CFG)
        assert len(s.protocol_events) == 1
        ev = s.protocol_events[0]
        assert ev.event_type == "DATA"
        assert ev.protocol == "udp"
        assert ev.payload_size == 500
        assert ev.src_port == 12345
        assert ev.dst_port == 80
        assert ev.timestamp == pytest.approx(0.0)

    def test_no_tcp_handshake_for_udp(self):
        s = build_demo_scenario(); s.clear()
        flow = TrafficFlow(
            source="PC1", destination="PC2", protocol="udp",
            size_bytes=500, count=1,
        )
        simulate_flow(s, flow, CFG)
        types = {e.event_type for e in s.protocol_events}
        assert types == {"DATA"}
        assert "SYN" not in types


class TestUdpPerPacketResult:
    def test_result_carries_udp_event(self):
        s = build_demo_scenario(); s.clear()
        flow = TrafficFlow(
            source="PC1", destination="PC2", protocol="udp",
            size_bytes=500, count=1,
        )
        r = simulate_flow(s, flow, CFG)
        assert len(r.events) == 1
        assert r.events[0].event_type == "DATA"
        assert r.events[0].protocol == "udp"


class TestProtocolEventPortFields:
    def test_ports_optional_and_default_none(self):
        e = ProtocolEvent(timestamp=0.0, source="A", destination="B",
                          protocol="tcp", event_type="SYN", packet_id=1)
        assert e.src_port is None
        assert e.dst_port is None

    def test_ports_storable(self):
        e = ProtocolEvent(timestamp=0.0, source="A", destination="B",
                          protocol="tcp", event_type="SYN", packet_id=1,
                          src_port=12345, dst_port=80)
        assert e.src_port == 12345
        assert e.dst_port == 80
