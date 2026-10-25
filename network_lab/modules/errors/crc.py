"""CRC error detection simulation.

Implements a simple CRC-8 for teaching purposes. Not a production CRC.
"""
from __future__ import annotations

from typing import Tuple


# Simple CRC-8 polynomial (CRC-8-CCITT-ish)
CRC8_POLY = 0x07
CRC8_INIT = 0x00


def _crc8_update(crc: int, byte: int) -> int:
    crc ^= byte
    for _ in range(8):
        if crc & 0x80:
            crc = ((crc << 1) ^ CRC8_POLY) & 0xFF
        else:
            crc = (crc << 1) & 0xFF
    return crc


def compute_crc8(data: bytes) -> int:
    """Compute a CRC-8 over the data bytes."""
    crc = CRC8_INIT
    for b in data:
        crc = _crc8_update(crc, b)
    return crc


def verify_crc8(data: bytes, expected_crc: int) -> bool:
    """Verify CRC-8: recompute over data and compare."""
    return compute_crc8(data) == expected_crc


def inject_error(data: bytes, bit_position: int = 0) -> bytes:
    """Flip a single bit to simulate a transmission error."""
    if not data:
        return data
    flipped = data[0] ^ (1 << (bit_position % 8))
    return bytes([flipped]) + data[1:]


def crc_with_error_detection(
    payload: bytes, error_injected: bool = False
) -> Tuple[bool, str]:
    """Run a complete CRC-based transmission simulation.

    Returns (error_detected, method).
    """
    crc = compute_crc8(payload)
    transmitted = payload + bytes([crc])

    if error_injected:
        transmitted = inject_error(transmitted, bit_position=0)

    received_payload = transmitted[:-1]
    received_crc = transmitted[-1]
    ok = verify_crc8(received_payload, received_crc)
    return (not ok, "crc")
