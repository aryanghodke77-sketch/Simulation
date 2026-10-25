"""Tests for error-detection modules (parity, checksum, CRC).

These assert actual detection behavior, not just that functions exist.
"""
from __future__ import annotations

import pytest

from network_lab.core.models import Device, Link, NetworkScenario

from network_lab.modules.errors.parity import (
    compute_parity,
    verify_parity,
    inject_error,
    parity_bit,
)
from network_lab.modules.errors.checksum import (
    compute_checksum,
    verify_checksum,
    inject_error as checksum_inject,
    checksum_with_error_detection,
)
from network_lab.modules.errors.crc import (
    compute_crc8,
    verify_crc8,
    inject_error as crc_inject,
    crc_with_error_detection,
)
from network_lab.modules.errors.engine import detect_error, compare_methods


class TestParity:
    def test_parity_bit_even(self):
        # 0x00 has 0 ones -> even parity bit 0
        assert parity_bit(0x00, even=True) == 0
        # 0x01 has 1 one -> even parity bit 1
        assert parity_bit(0x01, even=True) == 1
        # 0xFF has 8 ones -> even parity bit 0
        assert parity_bit(0xFF, even=True) == 0
        # 0x48 = 01001000 has 2 ones -> even parity bit 0
        assert parity_bit(0x48, even=True) == 0

    def test_parity_bit_odd(self):
        assert parity_bit(0x00, even=False) == 1
        assert parity_bit(0x01, even=False) == 0

    def test_compute_parity_single_byte(self):
        tb, p = compute_parity(b"\x00")
        assert tb == b"\x00\x00"
        assert p == 0

        tb, p = compute_parity(b"\x01")
        assert tb == b"\x01\x01"
        assert p == 1

        tb, p = compute_parity(b"\xff")
        assert tb == b"\xff\x00"
        assert p == 0

    def test_compute_parity_multi_byte(self):
        tb, p = compute_parity(b"Hi")
        # 'H' = 0x48 (2 ones), 'i' = 0x69 (4 ones) -> total 6 ones -> even -> parity 0
        assert tb == b"Hi\x00"
        assert p == 0

        tb, p = compute_parity(b"HH")
        # 2 + 2 = 4 ones -> even -> parity 0
        assert tb == b"HH\x00"
        assert p == 0

    def test_verify_parity_no_error(self):
        tb, p = compute_parity(b"Hi")
        assert verify_parity(tb, p) is True

    def test_verify_parity_detects_odd_flip(self):
        tb, p = compute_parity(b"Hi")
        for bp in range(8):
            fe = inject_error(tb, bit_position=bp)
            assert verify_parity(fe, p) is False, f"bit {bp} should be detected"

    def test_verify_parity_detects_in_engine(self):
        res = detect_error(b"Hi", method="parity", inject_error=True, error_location=0)
        assert res["error_injected"] is True
        assert res["error_detected"] is True
        assert res["details"]["payload_bytes"] == 2
        assert res["details"]["parity_type"] == "even"

    def test_parity_no_injection_not_detected(self):
        res = detect_error(b"Hi", method="parity", inject_error=False)
        assert res["error_injected"] is False
        assert res["error_detected"] is False

    def test_parity_compare_all(self):
        results = compare_methods(b"Hi", inject_error=True)
        by_method = {r["method"]: r for r in results}
        assert by_method["parity"]["error_detected"] is True
        assert by_method["checksum"]["error_detected"] is True
        assert by_method["crc"]["error_detected"] is True


class TestChecksum:
    def test_compute_checksum(self):
        cs = compute_checksum(b"Hi")
        # 'H'=0x48, 'i'=0x69 -> sum = 0xB1; one's complement 8-bit -> 0x4E
        assert cs == 0x4E

    def test_verify_checksum_no_error(self):
        cs = compute_checksum(b"Hi")
        assert verify_checksum(b"Hi", cs) is True

    def test_verify_checksum_detects_flip(self):
        cs = compute_checksum(b"Hi")
        corrupted = checksum_inject(b"Hi", byte_index=0, flip_mask=0x01)
        assert verify_checksum(corrupted[:-1], cs) is False

    def test_checksum_with_error_detection(self):
        detected, _ = checksum_with_error_detection(b"Hi", error_injected=True)
        assert detected is True

        detected, _ = checksum_with_error_detection(b"Hi", error_injected=False)
        assert detected is False

    def test_checksum_in_engine(self):
        res = detect_error(b"Hi", method="checksum", inject_error=True)
        assert res["error_injected"] is True
        assert res["error_detected"] is True
        assert res["details"]["checksum_decimal"] == compute_checksum(b"Hi")


class TestScenarioSerialization:
    def test_compute_crc8(self):
        crc = compute_crc8(b"Hi")
        assert 0 <= crc <= 0xFF

    def test_verify_crc8_no_error(self):
        crc = compute_crc8(b"Hi")
        assert verify_crc8(b"Hi", crc) is True

    def test_verify_crc8_detects_flip(self):
        crc = compute_crc8(b"Hi")
        corrupted = crc_inject(b"Hi", bit_position=0)
        assert verify_crc8(corrupted, crc) is False

    def test_crc_with_error_detection(self):
        detected, _ = crc_with_error_detection(b"Hi", error_injected=True)
        assert detected is True

        detected, _ = crc_with_error_detection(b"Hi", error_injected=False)
        assert detected is False

    def test_crc_in_engine(self):
        res = detect_error(b"Hi", method="crc", inject_error=True)
        assert res["error_injected"] is True
        assert res["error_detected"] is True
        assert res["details"]["crc_decimal"] == compute_crc8(b"Hi")

    def test_crc_detects_multiple_bit_flips(self):
        crc = compute_crc8(b"Hi")
        for bp in (0, 1, 3, 7):
            corrupted = crc_inject(b"Hi", bit_position=bp)
            assert verify_crc8(corrupted, crc) is False, f"bit {bp} should be detected"

class TestScenarioSerialization:
    def _make_scenario(self) -> NetworkScenario:
        sc = NetworkScenario("Demo")
        pc = sc.add_device("PC_A", kind="pc", ip="10.0.0.1")
        pc.add_interface("eth1")
        sc.add_device("PC_B", kind="pc")
        sw = sc.add_device("SW1", kind="switch")
        sc.connect("PC_A", "SW1")
        sc.connect("SW1", "PC_B")
        sc.assign_ip("PC_B", "eth0", "10.0.0.2")
        sc.subnets["10.0.0.0/24"] = "LAN"
        sc.metadata["course"] = "DCN"
        return sc

    def test_roundtrip_keeps_topology(self) -> None:
        sc = self._make_scenario()
        data = sc.to_dict()
        restored = NetworkScenario.from_dict(data)
        assert restored.name == sc.name
        assert set(restored.devices.keys()) == set(sc.devices.keys())
        assert {d.kind for d in restored.devices.values()} == {d.kind for d in sc.devices.values()}
        restored_ifaces = {
            (dn, iname, i.ip)
            for dn, d in restored.devices.items()
            for iname, i in d.interfaces.items()
        }
        orig_ifaces = {
            (dn, iname, i.ip)
            for dn, d in sc.devices.items()
            for iname, i in d.interfaces.items()
        }
        assert restored_ifaces == orig_ifaces
        assert [Link(l["a"], l["a_iface"], l["b"], l["b_iface"]) for l in data["links"]] == sc.links
        assert restored.links == sc.links
        assert restored.subnets == sc.subnets
        assert restored.metadata == sc.metadata

    def test_load_replaces_current_scenario(self) -> None:
        sc = self._make_scenario()
        assert len(sc.links) == 2
        assert sc.subnets == {"10.0.0.0/24": "LAN"}
        restored = NetworkScenario.from_dict(sc.to_dict())
        sc.name = restored.name
        sc.devices.clear()
        sc.links.clear()
        sc.subnets.clear()
        sc.metadata.clear()
        for dname, dev in restored.devices.items():
            sc.devices[dname] = dev
        sc.links.extend(restored.links)
        sc.subnets.update(restored.subnets)
        sc.metadata.update(restored.metadata)
        assert sc.name == "Demo"
        assert len(sc.links) == 2
        assert "10.0.0.0/24" in sc.subnets
        assert sc.metadata["course"] == "DCN"
        assert "PC_A" in sc.devices and sc.devices["PC_A"].kind == "pc"

    def test_serialization_excludes_transient_artifacts(self) -> None:
        from network_lab.simulation.traffic import TrafficFlow, SimulationConfig
        sc = self._make_scenario()
        flow = TrafficFlow(source="PC_A", destination="PC_B", protocol="tcp", size_bytes=100, count=1)
        sc.run_flow(flow, config=SimulationConfig())
        assert len(sc.packets) >= 1
        data = sc.to_dict()
        assert "packets" not in data
        assert "protocol_events" not in data
        assert "simulation_results" not in data
