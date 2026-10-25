"""Checksum error detection simulation.

Implements a simple 8-bit one's complement checksum for teaching purposes.
"""
from __future__ import annotations

from typing import Tuple


def compute_checksum(data: bytes) -> int:
    """Compute an 8-bit one's complement checksum of the data bytes."""
    total = 0
    for b in data:
        total += b
    # one's complement (8-bit): invert lower 8 bits
    while total > 0xFF:
        total = (total & 0xFF) + (total >> 8)
    return (~total) & 0xFF


def verify_checksum(data: bytes, expected_checksum: int) -> bool:
    """Verify checksum: data bytes + received checksum should sum to 0xFF.

    Uses one's-complement addition (carry wrapped into the low byte) so
    that a correct transmission sums to 0xFF.
    """
    total = 0
    for b in data:
        total += b
    total += expected_checksum
    while total > 0xFF:
        total = (total & 0xFF) + (total >> 8)
    return total == 0xFF


def inject_error(data: bytes, byte_index: int = 0, flip_mask: int = 0xFF) -> bytes:
    """Corrupt a byte to simulate a transmission error."""
    if not data or byte_index >= len(data):
        return data
    corrupted = bytearray(data)
    corrupted[byte_index] ^= flip_mask & 0xFF
    return bytes(corrupted)


def checksum_with_error_detection(
    payload: bytes, error_injected: bool = False
) -> Tuple[bool, str]:
    """Run a complete checksum-based transmission simulation.

    Returns (error_detected, method).
    """
    checksum = compute_checksum(payload)
    transmitted = payload + bytes([checksum])

    if error_injected:
        transmitted = inject_error(transmitted, byte_index=0, flip_mask=0x01)

    # receiver re-separates payload and checksum
    received_payload = transmitted[:-1]
    received_checksum = transmitted[-1]
    ok = verify_checksum(received_payload, received_checksum)
    return (not ok, "checksum")
