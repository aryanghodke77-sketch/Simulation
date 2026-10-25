"""Tests for core domain models and scenario behavior."""
from __future__ import annotations

import pytest

from network_lab.core import NetworkScenario
from network_lab.core.models import Device, Interface, Link
from network_lab.core.protocols import Packet, ProtocolEvent, SimulationResult


class TestNetworkScenarioDevices:
    def test_add_device_defaults(self):
        s = NetworkScenario("T")
        d = s.add_device("PC1", "pc")
        assert d.name == "PC1"
        assert d.kind == "pc"
        assert "eth0" in d.interfaces
        assert s.devices["PC1"] is d

    def test_add_device_custom_interface(self):
        s = NetworkScenario("T")
        s.add_device("R1", "router", interfaces={"eth0": None, "eth1": None})
        r = s.devices["R1"]
        assert set(r.interfaces.keys()) == {"eth0", "eth1"}

    def test_duplicate_device_raises(self):
        s = NetworkScenario("T")
        s.add_device("PC1", "pc")
        with pytest.raises(ValueError, match="already exists"):
            s.add_device("PC1", "pc")

    def test_remove_device(self):
        s = NetworkScenario("T")
        s.add_device("PC1", "pc")
        s.add_device("PC2", "pc")
        s.connect("PC1", "PC2")
        assert len(s.devices) == 2
        assert len(s.links) == 1
        s.remove_device("PC1")
        assert "PC1" not in s.devices
        assert s.links == []

    def test_device_interface_assignment(self):
        s = NetworkScenario("T")
        s.add_device("PC1", "pc")
        s.assign_ip("PC1", "eth0", "192.168.1.10")
        iface = s.devices["PC1"].interfaces["eth0"]
        assert iface.ip == "192.168.1.10"


class TestLinks:
    def test_connect_auto_ifaces(self):
        s = NetworkScenario("T")
        s.add_device("A", "pc")
        s.add_device("B", "pc")
        link = s.connect("A", "B")
        assert link.a == "A"
        assert link.b == "B"
        # add_device created eth0 on each device, so the next free interface is eth1.
        assert link.a_iface == "eth1"
        assert link.b_iface == "eth1"

    def test_connect_explicit_ifaces(self):
        s = NetworkScenario("T")
        s.add_device("A", "pc")
        s.add_device("B", "pc")
        link = s.connect("A", "B", a_iface="eth0", b_iface="eth0")
        assert link.a_iface == "eth0"
        assert link.b_iface == "eth0"

    def test_connect_custom_ifaces(self):
        s = NetworkScenario("T")
        s.add_device("R", "router", interfaces={"eth0": None, "eth1": None})
        s.add_device("PC", "pc")
        link = s.connect("R", "PC", a_iface="eth1", b_iface="eth0")
        assert link.a_iface == "eth1"
        assert link.b_iface == "eth0"

    def test_connect_missing_device_raises(self):
        s = NetworkScenario("T")
        s.add_device("A", "pc")
        with pytest.raises(ValueError, match="existing devices"):
            s.connect("A", "B")

    def test_disconnect(self):
        s = NetworkScenario("T")
        s.add_device("A", "pc")
        s.add_device("B", "pc")
        s.add_device("C", "pc")
        s.connect("A", "B")
        s.connect("A", "C")
        s.disconnect("A", "B")
        assert len(s.links) == 1
        assert s.links[0].devices() == ("A", "C")


class TestPathFinding:
    def test_bfs_simple_path(self):
        s = NetworkScenario("T")
        s.add_device("PC1", "pc")
        s.add_device("Router", "router")
        s.add_device("PC2", "pc")
        s.connect("PC1", "Router")
        s.connect("Router", "PC2")
        path = s.find_path("PC1", "PC2")
        assert [d.name for d in path] == ["PC1", "Router", "PC2"]

    def test_path_names(self):
        s = NetworkScenario("T")
        s.add_device("A", "pc")
        s.add_device("B", "pc")
        s.connect("A", "B")
        assert s.find_path_names("A", "B") == ["A", "B"]

    def test_no_path_raises(self):
        s = NetworkScenario("T")
        s.add_device("A", "pc")
        s.add_device("B", "pc")
        with pytest.raises(ValueError, match="No path"):
            s.find_path("A", "B")

    def test_same_device_path(self):
        s = NetworkScenario("T")
        s.add_device("PC1", "pc")
        path = s.find_path("PC1", "PC1")
        assert len(path) == 1
        assert path[0].name == "PC1"

    def test_interfaces_on_path(self):
        s = NetworkScenario("T")
        s.add_device("PC1", "pc")
        s.add_device("Router", "router")
        s.add_device("PC2", "pc")
        s.connect("PC1", "Router")
        s.connect("Router", "PC2")
        ifaces = s.interfaces_on_path("PC1", "PC2")
        names = [n for n, _ in ifaces]
        assert names == ["PC1", "Router", "Router", "PC2"]


class TestNeighbors:
    def test_neighbors(self):
        s = NetworkScenario("T")
        s.add_device("A", "pc")
        s.add_device("B", "pc")
        s.add_device("C", "pc")
        s.connect("A", "B")
        s.connect("A", "C")
        assert set(s.neighbors("A")) == {"B", "C"}
        assert s.neighbors("B") == ["A"]
        assert s.neighbors("C") == ["A"]


class TestModelsStandalone:
    def test_interface_str(self):
        i = Interface(name="eth0", device="PC1", ip="10.0.0.2")
        assert str(i) == "PC1:eth0 [10.0.0.2]"

    def test_device_str(self):
        d = Device(name="PC1", kind="pc")
        assert "PC1" in str(d)

    def test_link_str(self):
        l = Link(a="A", a_iface="eth0", b="B", b_iface="eth0")
        assert "A:eth0" in str(l)

    def test_packet_default(self):
        p = Packet(id=1, timestamp=0.0, source="A", destination="B", protocol="tcp", size=100)
        assert p.id == 1
        assert p.protocol == "tcp"
        assert p.transit_time() is None

    def test_packet_transit_time(self):
        p = Packet(id=1, timestamp=0.0, source="A", destination="B", protocol="tcp", size=100,
                   journey=[{"time": 0.0}, {"time": 0.5}])
        assert p.transit_time() == 0.5

    def test_protocol_event(self):
        e = ProtocolEvent(timestamp=0.0, source="A", destination="B", protocol="tcp",
                          event_type="SYN", packet_id=1)
        assert e.event_type == "SYN"

    def test_simulation_result(self):
        p = Packet(id=1, timestamp=0.0, source="A", destination="B", protocol="tcp", size=100)
        r = SimulationResult(packet=p, events=[], start_time=0.0, end_time=1.0,
                             bandwidth_bps=800.0, bytes_transferred=100)
        assert r.transit_time == 1.0

    def test_scenario_summary_empty(self):
        s = NetworkScenario("T")
        assert s.summary()["devices"] == 0
        assert s.summary()["packets"] == 0

    def test_clear_simulation_artifacts(self):
        s = NetworkScenario("T")
        s.packets = [Packet(id=1, timestamp=0, source="A", destination="B", protocol="tcp", size=1)]
        s.protocol_events = [ProtocolEvent(timestamp=0, source="A", destination="B", protocol="tcp",
                                            event_type="SYN", packet_id=1)]
        s.simulation_results = [SimulationResult(packet=None, events=[], start_time=0, end_time=1)]
        s.clear()
        assert s.packets == []
        assert s.protocol_events == []
        assert s.simulation_results == []
