"""Parity error detection simulation.

Demonstrates even-parity over a single data byte for teaching purposes.

Model:
- compute_parity(data) -> (transmitted, parity_bit)
  where transmitted = data byte followed by the parity bit as its own byte.
- verify_parity(transmitted, expected_parity) -> bool
  recomputes even parity over the received data byte and compares it to the
  received parity bit. Returns True when no error is detected.
- inject_error(transmitted, bit_position) flips one bit to simulate a
  transmission error.
"""

from __future__ import annotations

from typing import Tuple


def parity_bit(byte: int, even: bool = True) -> int:
    """Return the even/odd parity bit (0/1) for a byte."""
    bits = bin(byte)[2:].zfill(8)
    ones = bits.count("1")
    if even:
        return 0 if ones % 2 == 0 else 1
    return 1 if ones % 2 == 0 else 0


def compute_parity(data: bytes, even: bool = True) -> Tuple[bytes, int]:
    """Return (transmitted_bytes, parity_bit).

    transmitted_bytes = data (unchanged) followed by a parity byte whose LSB
    is the even-parity bit over all data bytes. This protects the whole
    payload with a single parity byte (teachable model).
    """
    if not data:
        data = b"\x00"
    ones = sum(bin(b)[2:].count("1") for b in data)
    p = 0 if (ones % 2 == 0) == (even is True) else 1
    parity_byte = p & 0x01
    return bytes(list(data) + [parity_byte]), p


def verify_parity(data_with_parity: bytes, expected_parity: int, even: bool = True) -> bool:
    """Verify received data+parity. Returns True when no error detected.

    Recompute even parity over the received data bytes (all but the last)
    and compare to the received parity bit (the LSB of the last byte).
    """
    if len(data_with_parity) < 2:
        return expected_parity == 0
    data_bytes = data_with_parity[:-1]
    received_parity = data_with_parity[-1] & 0x01
    ones = sum(bin(b)[2:].count("1") for b in data_bytes)
    computed = 0 if (ones % 2 == 0) == (even is True) else 1
    return computed == received_parity


def inject_error(data: bytes, bit_position: int = 0) -> bytes:
    """Flip a single bit in the first byte to simulate a transmission error."""
    if not data:
        return data
    flipped = data[0] ^ (1 << (bit_position % 8))
    return bytes([flipped]) + data[1:]
