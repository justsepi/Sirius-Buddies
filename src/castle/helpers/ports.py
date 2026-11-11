"""Offline localhost port & TCP listener inspector."""

from dataclasses import dataclass, field
import re
import shutil
import socket
import subprocess
import sys

COMMON_DEV_PORTS: dict[int, str] = {
    3000: "Node / React",
    3001: "Dev UI",
    4000: "Phoenix / Dev",
    5000: "Flask / AirPlay",
    5173: "Vite",
    5432: "PostgreSQL",
    6379: "Redis",
    8000: "Python / FastAPI",
    8080: "HTTP Alt",
    8888: "Jupyter",
}


@dataclass
class PortEntry:
    """Single port status or listening socket entry."""

    port: int
    state: str
    process: str
    note: str


@dataclass
class PortReport:
    """Structured localhost port scan summary."""

    entries: list[PortEntry] = field(default_factory=list)
    listening_count: int = 0
    mood: str = "chill"
    comment: str = ""
    rows: list[tuple[str, str, str, str]] = field(default_factory=list)


def _probe_loopback(port: int, timeout: float = 0.04) -> bool:
    """Return True if localhost accepts a TCP connection on `port`."""
    for family, host in ((socket.AF_INET, "127.0.0.1"), (socket.AF_INET6, "::1")):
        try:
            with socket.socket(family, socket.SOCK_STREAM) as sock:
                sock.settimeout(timeout)
                if sock.connect_ex((host, port)) == 0:
                    return True
        except OSError:
            continue
    return False


def _run_cmd(cmd: list[str], timeout: float = 2.0) -> str:
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        if proc.returncode == 0:
            return proc.stdout
    except (OSError, subprocess.SubprocessError):
        pass
    return ""


def _windows_pid_map() -> dict[int, str]:
    out = _run_cmd(["tasklist", "/FO", "CSV", "/NH"], timeout=2.5)
    pid_map: dict[int, str] = {}
    for line in out.splitlines():
        parts = [p.strip().strip('"') for p in line.split('","')]
        if len(parts) >= 2 and parts[1].isdigit():
            pid_map[int(parts[1])] = parts[0]
    return pid_map


def _parse_windows_netstat(out: str, pid_map: dict[int, str]) -> dict[int, str]:
    listeners: dict[int, str] = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 5 and parts[0].upper() == "TCP" and parts[3].upper() == "LISTENING":
            addr = parts[1]
            port_str = addr.rsplit(":", 1)[-1]
            if port_str.isdigit():
                port = int(port_str)
                pid = int(parts[4]) if parts[4].isdigit() else None
                proc_name = pid_map.get(pid, f"PID {pid}" if pid else "listening")
                listeners.setdefault(port, proc_name)
    return listeners


def _parse_lsof_output(out: str) -> dict[int, str]:
    listeners: dict[int, str] = {}
    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 9:
            proc_name = f"{parts[0]} ({parts[1]})"
            m = re.search(r":(\d+)\s*(?:\(LISTEN\))?$", line)
            if m:
                listeners.setdefault(int(m.group(1)), proc_name)
    return listeners


def _discover_os_listeners() -> dict[int, str]:
    """Discover listening TCP ports and owning processes offline via OS tools."""
    listeners: dict[int, str] = {}

    if sys.platform == "win32":
        out = _run_cmd(["netstat", "-ano", "-p", "tcp"], timeout=2.5)
        if not out:
            return listeners
        return _parse_windows_netstat(out, _windows_pid_map())

    if shutil.which("lsof"):
        out = _run_cmd(["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"], timeout=2.5)
        listeners = _parse_lsof_output(out)
        if listeners:
            return listeners

    if shutil.which("ss"):
        out = _run_cmd(["ss", "-tln"], timeout=2.0)
        for line in out.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 4:
                port_str = parts[3].rsplit(":", 1)[-1]
                if port_str.isdigit():
                    listeners.setdefault(int(port_str), "listening")
        if listeners:
            return listeners

    out = _run_cmd(["netstat", "-an"], timeout=2.0)
    for line in out.splitlines():
        if "LISTEN" in line.upper():
            m = re.search(r"[.:](\d+)\s", line)
            if m:
                listeners.setdefault(int(m.group(1)), "listening")
    return listeners


def inspect_ports(custom_ports: list[int] | None = None) -> PortReport:
    """Inspect active OS TCP listeners and probe common or requested dev ports."""
    listeners = _discover_os_listeners()
    entries: list[PortEntry] = []

    if custom_ports:
        ports_to_check = sorted({p for p in custom_ports if 1 <= p <= 65535})
        for port in ports_to_check:
            active = port in listeners or _probe_loopback(port)
            proc = listeners.get(port, "local socket" if active else "-")
            entries.append(
                PortEntry(
                    port=port,
                    state="LISTENING" if active else "free",
                    process=proc,
                    note=COMMON_DEV_PORTS.get(port, "requested"),
                )
            )
    else:
        # Show all discovered active listeners first (up to 12), plus status of key dev ports
        seen: set[int] = set()
        for port in sorted(listeners):
            seen.add(port)
            entries.append(
                PortEntry(
                    port=port,
                    state="LISTENING",
                    process=listeners[port],
                    note=COMMON_DEV_PORTS.get(port, "active listener"),
                )
            )
            if len(entries) >= 12:
                break

        for port, label in COMMON_DEV_PORTS.items():
            if port in seen:
                continue
            active = _probe_loopback(port)
            if active:
                entries.append(
                    PortEntry(port=port, state="LISTENING", process="local socket", note=label)
                )
                seen.add(port)

        if not entries:
            for port in (3000, 5173, 8000, 8080):
                entries.append(
                    PortEntry(port=port, state="free", process="-", note=COMMON_DEV_PORTS[port])
                )

    listening_count = sum(1 for e in entries if e.state == "LISTENING")
    rows = [(str(e.port), e.state, e.process, e.note) for e in entries[:12]]

    if listening_count == 0:
        mood = "chill"
        comment = "Quiet on the dev ports, dude. Nothing squattin' on localhost."
    elif listening_count >= 6:
        mood = "curious"
        comment = f"Whoa, {listening_count} ports wide open and chattin', dude. Busy rig!"
    else:
        mood = "working"
        comment = f"Spotted {listening_count} active listener(s) on localhost, dude."

    return PortReport(
        entries=entries,
        listening_count=listening_count,
        mood=mood,
        comment=comment,
        rows=rows,
    )
