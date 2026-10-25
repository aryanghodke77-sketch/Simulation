"""Bandwidth analysis from simulation results.

Computes per-flow and aggregate bandwidth metrics and prepares time-series
data for Plotly visualization.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from network_lab.core.protocols import Packet, SimulationResult


def flow_bandwidth(result: SimulationResult) -> float:
    """Return bandwidth in bps for a simulation result."""
    return result.bandwidth_bps


def flow_transit_time(result: SimulationResult) -> float:
    """Return simulated end-to-end transit time in seconds."""
    return result.transit_time


def flow_throughput_bytes(result: SimulationResult) -> int:
    return result.bytes_transferred


def aggregate_bandwidth(results: List[SimulationResult]) -> float:
    """Average bandwidth across results in bps."""
    if not results:
        return 0.0
    return sum(r.bandwidth_bps for r in results) / len(results)


def total_bytes_transferred(results: List[SimulationResult]) -> int:
    return sum(r.bytes_transferred for r in results)


def bandwidth_time_series(
    packets: List[Packet], link_rate_bps: float = 1_000_000.0
) -> List[Dict[str, Any]]:
    """Build a simple time-series of cumulative bytes vs. time for plotting.

    Each entry: {time, cumulative_bytes, instantaneous_bps}
    """
    if not packets:
        return []

    sorted_packets = sorted(packets, key=lambda p: p.timestamp)
    series: List[Dict[str, Any]] = []
    cumulative = 0
    prev_time = sorted_packets[0].timestamp

    for p in sorted_packets:
        cumulative += p.size
        dt = p.timestamp - prev_time if p.timestamp > prev_time else 1e-9
        # instantaneous bandwidth from this packet's contribution over its transit
        transit = p.transit_time() or dt
        inst_bps = (p.size * 8) / transit if transit > 0 else 0.0
        series.append({
            "time": p.timestamp,
            "cumulative_bytes": cumulative,
            "instantaneous_bps": inst_bps,
            "packet_id": p.id,
        })
        prev_time = p.timestamp

    return series


def bandwidth_summary(
    packets: List[Packet], results: List[SimulationResult]
) -> Dict[str, Any]:
    """High-level bandwidth stats for the dashboard."""
    return {
        "total_bytes": sum(p.size for p in packets),
        "total_packets": len(packets),
        "avg_bandwidth_bps": aggregate_bandwidth(results),
        "peak_bandwidth_bps": max((r.bandwidth_bps for r in results), default=0.0),
        "total_transferred_bytes": total_bytes_transferred(results),
        "time_series": bandwidth_time_series(packets),
    }
