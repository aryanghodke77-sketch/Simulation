"""Real network interface monitoring (live host), separate from simulation.

Uses psutil to read bytes sent/received on real interfaces and computes
live bandwidth. This is intentionally separate from the simulated network
so the two are not mixed in the UI.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    import psutil
    _HAS_PSUTIL = True
except Exception:  # psutil may not be installed in all environments
    _HAS_PSUTIL = False


def get_interfaces() -> List[str]:
    """List network interface names available on the host."""
    if not _HAS_PSUTIL:
        return []
    return list(psutil.net_io_counters(pernic=True).keys())


def interface_stats(interface: str) -> Optional[Dict[str, Any]]:
    """Return bytes sent/received and timestamps for a real interface.

    Returns None if the interface doesn't exist or psutil is unavailable.
    """
    if not _HAS_PSUTIL:
        return None
    counters = psutil.net_io_counters(pernic=True)
    if interface not in counters:
        return None
    c = counters[interface]
    return {
        "interface": interface,
        "bytes_sent": c.bytes_sent,
        "bytes_recv": c.bytes_recv,
        "packets_sent": getattr(c, "packets_sent", 0),
        "packets_recv": getattr(c, "packets_recv", 0),
        "errin": getattr(c, "errin", 0),
        "errout": getattr(c, "errout", 0),
        "dropin": getattr(c, "dropin", 0),
        "dropout": getattr(c, "dropout", 0),
    }


def live_bandwidth(
    interface: Optional[str] = None, duration_seconds: float = 1.0
) -> Dict[str, Any]:
    """Measure live send/receive bandwidth on an interface over a short window.

    Returns a dict with bytes and bps in each direction. If no interface is
    given, uses the first available interface.
    """
    if not _HAS_PSUTIL:
        return {"error": "psutil not available", "interface": interface}

    interfaces = get_interfaces()
    if not interfaces:
        return {"error": "no network interfaces available", "interface": interface}

    iface = interface or interfaces[0]
    before = interface_stats(iface)
    if before is None:
        return {"error": f"interface '{iface}' not found", "interface": iface}

    import time
    time.sleep(duration_seconds)

    after = interface_stats(iface)
    if after is None:
        return {"error": f"interface '{iface}' disappeared", "interface": iface}

    sent = after["bytes_sent"] - before["bytes_sent"]
    recv = after["bytes_recv"] - before["bytes_recv"]
    # guard against spurious negative values from counter wraps
    sent = max(0, sent)
    recv = max(0, recv)

    return {
        "interface": iface,
        "duration_seconds": duration_seconds,
        "bytes_sent": sent,
        "bytes_recv": recv,
        "send_bps": (sent * 8) / duration_seconds,
        "recv_bps": (recv * 8) / duration_seconds,
        "total_bps": ((sent + recv) * 8) / duration_seconds,
    }
