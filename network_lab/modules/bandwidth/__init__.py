"""Bandwidth module: simulated traffic analysis and real interface monitoring."""

from network_lab.modules.bandwidth.analyzer import (
    aggregate_bandwidth,
    bandwidth_summary,
    bandwidth_time_series,
    flow_bandwidth,
    flow_transit_time,
    flow_throughput_bytes,
    total_bytes_transferred,
)
from network_lab.modules.bandwidth.monitor import (
    get_interfaces,
    interface_stats,
    live_bandwidth,
)

__all__ = [
    "aggregate_bandwidth",
    "bandwidth_summary",
    "bandwidth_time_series",
    "flow_bandwidth",
    "flow_transit_time",
    "flow_throughput_bytes",
    "total_bytes_transferred",
    "get_interfaces",
    "interface_stats",
    "live_bandwidth",
]
