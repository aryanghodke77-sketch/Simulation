"""Error detection engine.

Orchestrates parity, checksum, and CRC simulations over a payload, with
optional error injection, and returns structured results for the UI.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from network_lab.modules.errors.parity import (
    inject_error as parity_inject,
    verify_parity,
    compute_parity,
    parity_bit,
)
from network_lab.modules.errors.checksum import (
    checksum_with_error_detection,
    compute_checksum,
    inject_error as checksum_inject,
)
from network_lab.modules.errors.crc import (
    crc_with_error_detection,
    compute_crc8,
    inject_error as crc_inject,
)


def detect_error(
    payload: bytes,
    method: str = "crc",
    inject_error: bool = False,
    error_location: int = 0,
) -> Dict[str, Any]:
    """Run one error-detection method over a payload and return the result.

    method: 'parity', 'checksum', 'crc'
    """
    if method == "parity":
        pbytes, pbit = compute_parity(payload)
        if inject_error:
            pbytes = parity_inject(pbytes, bit_position=error_location)
        detected = not verify_parity(pbytes, pbit)
        return {
            "method": "parity",
            "error_injected": inject_error,
            "error_detected": detected,
            "details": {
                "parity_type": "even",
                "parity_bit": pbit,
                "payload_hex": payload.hex(),
                "payload_bytes": len(payload),
                "transmitted_hex": pbytes.hex(),
                "expected_parity": pbit,
            },
        }

    if method == "checksum":
        detected, _ = checksum_with_error_detection(payload, error_injected=inject_error)
        checksum = compute_checksum(payload)
        return {
            "method": "checksum",
            "error_injected": inject_error,
            "error_detected": detected,
            "details": {
                "payload_hex": payload.hex(),
                "checksum_hex": f"{checksum:02X}",
                "checksum_decimal": checksum,
            },
        }

    if method == "crc":
        detected, _ = crc_with_error_detection(payload, error_injected=inject_error)
        crc = compute_crc8(payload)
        return {
            "method": "crc",
            "error_injected": inject_error,
            "error_detected": detected,
            "details": {
                "payload_hex": payload.hex(),
                "crc_hex": f"{crc:02X}",
                "crc_decimal": crc,
            },
        }

    raise ValueError(f"Unknown error detection method: {method}")


def compare_methods(
    payload: bytes, inject_error: bool = False, error_location: int = 0
) -> List[Dict[str, Any]]:
    """Run all error-detection methods over the same payload and return results."""
    results: List[Dict[str, Any]] = []
    for method in ("parity", "checksum", "crc"):
        results.append(detect_error(payload, method=method, inject_error=inject_error,
                                   error_location=error_location))
    return results
