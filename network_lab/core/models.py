"""Core domain models for the Network Lab simulation.

Devices, interfaces, links, and the NetworkScenario that ties them together.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple




@dataclass
class Interface:
    name: str
    device: str  # device name this interface belongs to
    ip: Optional[str] = None
    mac: Optional[str] = None

    def __str__(self) -> str:
        return f"{self.device}:{self.name}" + (f" [{self.ip}]" if self.ip else "")


@dataclass
class Device:
    name: str
    kind: str  # 'pc', 'router', 'switch', ...
    interfaces: Dict[str, Interface] = field(default_factory=dict)
    ip: Optional[str] = None  # "primary" IP for simpler UI; real addressing is per-interface

    def add_interface(self, iface_name: str, ip: Optional[str] = None,
                      mac: Optional[str] = None) -> Interface:
        iface = Interface(name=iface_name, device=self.name, ip=ip, mac=mac)
        self.interfaces[iface_name] = iface
        return iface

    def __str__(self) -> str:
        iface_str = ", ".join(str(i) for i in self.interfaces.values()) or "no interfaces"
        return f"{self.kind.capitalize()} {self.name} ({iface_str})"


@dataclass
class Link:
    a: str  # device name
    a_iface: str
    b: str
    b_iface: str

    def devices(self) -> Tuple[str, str]:
        return (self.a, self.b)

    def __str__(self) -> str:
        return f"{self.a}:{self.a_iface} <-> {self.b}:{self.b_iface}"


class NetworkScenario:
    """The central shared model for the whole application.

    A scenario owns devices, interfaces, links, IP addressing, and
    downstream artifacts (packets, protocol events, simulation results).
    """

    def __init__(self, name: str = "Untitled Scenario") -> None:
        self.name = name
        self.devices: Dict[str, Device] = {}
        self.links: List[Link] = []
        self.subnets: Dict[str, str] = {}  # subnet cidr -> description
        self.packets: List["Packet"] = []
        self.protocol_events: List["ProtocolEvent"] = []
        self.simulation_results: List["SimulationResult"] = []
        self.metadata: Dict[str, str] = {}

    # ---- devices ----
    def add_device(self, name: str, kind: str = "pc",
                   ip: Optional[str] = None,
                   interfaces: Optional[Dict[str, Optional[str]]] = None) -> Device:
        if name in self.devices:
            raise ValueError(f"Device '{name}' already exists")
        dev = Device(name=name, kind=kind, ip=ip)
        if interfaces:
            for iface_name, iface_ip in interfaces.items():
                dev.add_interface(iface_name, ip=iface_ip)
        else:
            dev.add_interface("eth0", ip=None)
        self.devices[name] = dev
        return dev

    def remove_device(self, name: str) -> None:
        if name not in self.devices:
            raise ValueError(f"Device '{name}' not found")
        self.devices.pop(name)
        self.links = [l for l in self.links if l.a != name and l.b != name]

    def connect(self, a: str, b: str,
                a_iface: Optional[str] = None, b_iface: Optional[str] = None) -> Link:
        if a not in self.devices or b not in self.devices:
            raise ValueError("Both endpoints must be existing devices")
        if a_iface is None:
            a_iface = self._next_iface(a)
        if b_iface is None:
            b_iface = self._next_iface(b)
        link = Link(a=a, a_iface=a_iface, b=b, b_iface=b_iface)
        self.links.append(link)
        return link

    def disconnect(self, a: str, b: str) -> None:
        self.links = [l for l in self.links
                      if not ((l.a == a and l.b == b) or (l.a == b and l.b == a))]

    # ---- addressing ----
    def assign_ip(self, device: str, interface: str, ip: str) -> None:
        if device not in self.devices:
            raise ValueError(f"Device '{device}' not found")
        dev = self.devices[device]
        if interface not in dev.interfaces:
            dev.add_interface(interface, ip=ip)
        else:
            dev.interfaces[interface].ip = ip

    def device_interface(self, device: str, interface: str = "eth0") -> Interface:
        dev = self.devices[device]
        if interface not in dev.interfaces:
            dev.add_interface(interface)
        return dev.interfaces[interface]

    # ---- topology ----
    def neighbors(self, device: str) -> List[str]:
        out: List[str] = []
        for l in self.links:
            if l.a == device:
                out.append(l.b)
            elif l.b == device:
                out.append(l.a)
        return out

    def _next_iface(self, device: str) -> str:
        dev = self.devices[device]
        n = len(dev.interfaces)
        if n == 0:
            return "eth0"
        return f"eth{n}"

    def clear(self) -> None:
        """Reset transient simulation artifacts while keeping the topology."""
        self.packets.clear()
        self.protocol_events.clear()
        self.simulation_results.clear()

    def neighbors_with_iface(self, device: str) -> List[Tuple[str, str]]:
        out: List[Tuple[str, str]] = []
        for l in self.links:
            if l.a == device:
                out.append((l.b, l.a_iface))
            elif l.b == device:
                out.append((l.a, l.b_iface))
        return out

    def find_path(self, source: str, destination: str) -> List[Device]:
        """Find a path from source to destination using BFS over links.

        Returns the list of Device objects in order from source to destination.
        Raises ValueError if no path exists.
        """
        if source not in self.devices or destination not in self.devices:
            raise ValueError("Both source and destination must be devices in the scenario")
        if source == destination:
            return [self.devices[source]]

        queue: List[Tuple[str, List[str]]] = [(source, [source])]
        visited: set = {source}
        while queue:
            current, path = queue.pop(0)
            for neighbor in self.neighbors(current):
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                new_path = path + [neighbor]
                if neighbor == destination:
                    return [self.devices[n] for n in new_path]
                queue.append((neighbor, new_path))
        raise ValueError(f"No path found between '{source}' and '{destination}'")

    def find_path_names(self, source: str, destination: str) -> List[str]:
        return [d.name for d in self.find_path(source, destination)]

    def interfaces_on_path(self, source: str, destination: str) -> List[Tuple[str, str]]:
        """Return list of (device, interface) pairs the packet traverses.

        Includes source interface (egress) and destination interface (ingress).
        """
        path_names = self.find_path_names(source, destination)
        steps: List[Tuple[str, str]] = []
        for i, dev_name in enumerate(path_names):
            if i == 0:
                # source egress interface: any interface connected toward next hop
                nxt = path_names[1]
                iface = self._iface_toward(dev_name, nxt)
                steps.append((dev_name, iface))
            elif i == len(path_names) - 1:
                # destination ingress interface
                prev = path_names[-2]
                iface = self._iface_toward(dev_name, prev)
                steps.append((dev_name, iface))
            else:
                # intermediate router: ingress from prev, egress to next
                prev = path_names[i - 1]
                nxt = path_names[i + 1]
                in_iface = self._iface_toward(dev_name, prev)
                out_iface = self._iface_toward(dev_name, nxt)
                steps.append((dev_name, in_iface))
                steps.append((dev_name, out_iface))
        return steps

    def _iface_toward(self, device: str, other: str) -> str:
        for l in self.links:
            if l.a == device and l.b == other:
                return l.a_iface
            if l.b == device and l.a == other:
                return l.b_iface
        # fallback
        return self.devices[device].interfaces[list(self.devices[device].interfaces.keys())[0]].name

    # ---- convenience ----
    def summary(self) -> Dict:
        return {
            "name": self.name,
            "devices": len(self.devices),
            "links": len(self.links),
            "subnets": len(self.subnets),
            "packets": len(self.packets),
            "protocol_events": len(self.protocol_events),
            "simulation_results": len(self.simulation_results),
        }

    def run_flow(
        self,
        flow: TrafficFlow,
        config: Optional[SimulationConfig] = None,
        error_detection_method: Optional[str] = None,
        error_inject_on_packet: Optional[int] = None,
    ) -> SimulationResult:
        """Run a traffic flow and record simulation results.

        If error_detection_method is set, each packet's payload is tested with
        the chosen method after injection (if any packet is targeted).
        """
        from network_lab.simulation.traffic import SimulationConfig as _SC
        from network_lab.simulation.network import simulate_flow as _simulate
        base = config if config is not None else SimulationConfig()
        kwargs: Dict[str, Any] = {
            "hop_delay": base.hop_delay,
            "processing_delay": base.processing_delay,
            "link_rate_bps": base.link_rate_bps,
            "error_injection_rate": base.error_injection_rate,
            "seed": base.seed,
            "error_detection_method": error_detection_method,
            "error_inject_on_packet": error_inject_on_packet,
        }
        cfg = _SC(**kwargs)
        result = _simulate(self, flow, config=cfg)
        return result

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the scenario topology (persistent state) to a JSON-friendly dict.

        Transient simulation artifacts (packets, events, results) are intentionally
        omitted — they are regenerated by running flows, not restored from disk.
        """
        devices: Dict[str, Any] = {}
        for dname, dev in self.devices.items():
            devices[dname] = {
                "kind": dev.kind,
                "ip": dev.ip,
                "interfaces": {
                    iname: {
                        "ip": iface.ip,
                        "mac": iface.mac,
                    }
                    for iname, iface in dev.interfaces.items()
                },
            }
        return {
            "name": self.name,
            "devices": devices,
            "links": [
                {"a": l.a, "a_iface": l.a_iface, "b": l.b, "b_iface": l.b_iface}
                for l in self.links
            ],
            "subnets": dict(self.subnets),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NetworkScenario":
        """Reconstruct a scenario from a dict produced by to_dict."""
        sc = cls(name=data.get("name", "Restored Scenario"))
        for dname, ddata in data.get("devices", {}).items():
            dev = sc.add_device(dname, kind=ddata.get("kind", "pc"), ip=ddata.get("ip"))
            for iname, idata in ddata.get("interfaces", {}).items():
                if iname not in dev.interfaces:
                    dev.add_interface(iname)
                if idata.get("ip"):
                    dev.interfaces[iname].ip = idata["ip"]
                if idata.get("mac"):
                    dev.interfaces[iname].mac = idata["mac"]
        for ldata in data.get("links", []):
            try:
                sc.connect(
                    ldata["a"], ldata["b"],
                    a_iface=ldata.get("a_iface"),
                    b_iface=ldata.get("b_iface"),
                )
            except ValueError:
                # stale link to a now-missing device — skip
                pass
        for cidr, desc in data.get("subnets", {}).items():
            sc.subnets[cidr] = desc
        for k, v in data.get("metadata", {}).items():
            sc.metadata[k] = v

        # ---- restore transient simulation artifacts (optional) ----
        for pkt_data in data.get("packets", []):
            try:
                sc.packets.append(Packet(**pkt_data))
            except TypeError:
                pass
        for ev_data in data.get("protocol_events", []):
            try:
                sc.protocol_events.append(ProtocolEvent(**ev_data))
            except TypeError:
                pass
        for res_data in data.get("simulation_results", []):
            try:
                sc.simulation_results.append(SimulationResult(**res_data))
            except TypeError:
                pass

        return sc

    def __str__(self) -> str:
        return (f"NetworkScenario({self.name!r}, devices={len(self.devices)}, "
                f"links={len(self.links)})")
