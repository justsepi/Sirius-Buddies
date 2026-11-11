"""Cross-platform offline system pulse & hardware vitals inspector."""

from dataclasses import dataclass, field
from datetime import datetime
import os
from pathlib import Path
import platform
import re
import shutil
import socket
import subprocess
import sys
import time


@dataclass
class DiskStat:
    """Disk usage snapshot for a single mount or drive."""

    label: str
    used_bytes: int
    total_bytes: int
    free_bytes: int
    percent: float


@dataclass
class SystemVitals:
    """Pure-offline system health summary."""

    hostname: str
    os_label: str
    arch: str
    shell: str
    python_version: str
    uptime: str
    cpu_cores: int
    cpu_detail: str
    ram_used: int | None = None
    ram_total: int | None = None
    ram_percent: float | None = None
    disks: list[DiskStat] = field(default_factory=list)
    battery_percent: int | None = None
    battery_plugged: bool | None = None
    local_ip: str = "127.0.0.1"


def format_bytes_human(num_bytes: int) -> str:
    """Format byte count concisely for terminal tables."""
    val = float(max(0, num_bytes))
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if val < 1024.0 or unit == "TB":
            if unit in ("B", "KB"):
                return f"{int(round(val))} {unit}"
            return f"{val:.1f} {unit}"
        val /= 1024.0
    return f"{num_bytes} B"


def _format_uptime(seconds: float) -> str:
    total_mins = max(0, int(seconds // 60))
    days, rem_mins = divmod(total_mins, 1440)
    hours, mins = divmod(rem_mins, 60)
    if days > 0:
        return f"{days}d {hours}h {mins}m"
    if hours > 0:
        return f"{hours}h {mins}m"
    return f"{mins}m"


def _progress_bar(pct: float, width: int = 10) -> str:
    clamped = max(0.0, min(100.0, pct))
    filled = int(round(clamped * width / 100.0))
    return "█" * filled + "░" * (width - filled)


def _detect_shell() -> str:
    msystem = os.environ.get("MSYSTEM", "").strip()
    wt = bool(os.environ.get("WT_SESSION"))
    shell_env = os.environ.get("SHELL", "").strip()
    if msystem:
        base = f"Git Bash ({msystem})"
        return f"{base} · WT" if wt else base
    if shell_env:
        name = Path(shell_env).name
        return f"{name} · WT" if wt else name
    if sys.platform == "win32":
        if os.environ.get("PSModulePath"):
            return "PowerShell · WT" if wt else "PowerShell"
        return "cmd · WT" if wt else "cmd"
    return os.name


def _detect_os_label() -> str:
    if sys.platform == "darwin":
        mac_ver = platform.mac_ver()[0]
        return f"macOS {mac_ver}" if mac_ver else "macOS"
    if sys.platform == "win32":
        rel = platform.release()
        try:
            build = sys.getwindowsversion().build
            if rel == "10" and build >= 22000:
                rel = "11"
        except Exception:
            pass
        return f"Windows {rel}"
    return f"{platform.system()} {platform.release()}".strip()


def _run_quick(cmd: list[str], timeout: float = 1.5) -> str:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if proc.returncode == 0:
            return proc.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return ""


def _get_uptime() -> str:
    if sys.platform == "win32":
        try:
            import ctypes

            ms = ctypes.windll.kernel32.GetTickCount64()
            return _format_uptime(ms / 1000.0)
        except Exception:
            return "n/a"

    if sys.platform == "darwin":
        out = _run_quick(["sysctl", "-n", "kern.boottime"])
        match = re.search(r"sec\s*=\s*(\d+)", out)
        if match:
            boot_sec = int(match.group(1))
            return _format_uptime(max(0.0, time.time() - boot_sec))
        return "n/a"

    proc_uptime = Path("/proc/uptime")
    if proc_uptime.exists():
        try:
            secs = float(proc_uptime.read_text(encoding="utf-8").split()[0])
            return _format_uptime(secs)
        except (OSError, ValueError, IndexError):
            pass
    return "n/a"


def _get_cpu_detail(cores: int) -> str:
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class FILETIME(ctypes.Structure):
                _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]

            def to_int(ft: FILETIME) -> int:
                return (ft.dwHighDateTime << 32) | ft.dwLowDateTime

            def sample() -> tuple[int, int, int]:
                idle, kernel, user = FILETIME(), FILETIME(), FILETIME()
                ctypes.windll.kernel32.GetSystemTimes(
                    ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)
                )
                return to_int(idle), to_int(kernel), to_int(user)

            i1, k1, u1 = sample()
            time.sleep(0.06)
            i2, k2, u2 = sample()
            total = (k2 - k1) + (u2 - u1)
            idle = i2 - i1
            if total > 0:
                busy = max(0.0, min(100.0, (1.0 - (idle / total)) * 100.0))
                return f"{cores} cores · {busy:.0f}% busy"
        except Exception:
            pass
        return f"{cores} cores"

    if hasattr(os, "getloadavg"):
        try:
            l1, l5, _ = os.getloadavg()
            return f"{cores} cores · load {l1:.2f} / {l5:.2f}"
        except OSError:
            pass
    return f"{cores} cores"


def _get_ram_info() -> tuple[int, int, float] | None:
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", wintypes.DWORD),
                    ("dwMemoryLoad", wintypes.DWORD),
                    ("ullTotalPhys", ctypes.c_uint64),
                    ("ullAvailPhys", ctypes.c_uint64),
                    ("ullTotalPageFile", ctypes.c_uint64),
                    ("ullAvailPageFile", ctypes.c_uint64),
                    ("ullTotalVirtual", ctypes.c_uint64),
                    ("ullAvailVirtual", ctypes.c_uint64),
                    ("sullAvailExtendedVirtual", ctypes.c_uint64),
                ]

            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
                total = int(stat.ullTotalPhys)
                avail = int(stat.ullAvailPhys)
                used = max(0, total - avail)
                pct = (used / total * 100.0) if total else float(stat.dwMemoryLoad)
                return used, total, pct
        except Exception:
            return None

    if sys.platform == "darwin":
        mem_raw = _run_quick(["sysctl", "-n", "hw.memsize"])
        vm_raw = _run_quick(["vm_stat"])
        if mem_raw.isdigit() and vm_raw:
            total = int(mem_raw)
            ps_match = re.search(r"page size of (\d+) bytes", vm_raw)
            page_size = int(ps_match.group(1)) if ps_match else 4096

            def _pages(label: str) -> int:
                m = re.search(rf"{re.escape(label)}:\s+(\d+)\.", vm_raw)
                return int(m.group(1)) if m else 0

            active = _pages("Pages active")
            wired = _pages("Pages wired down")
            compressed = _pages("Pages occupied by compressor")
            used = (active + wired + compressed) * page_size
            if used == 0:
                free_pages = _pages("Pages free") + _pages("Pages speculative")
                used = max(0, total - free_pages * page_size)
            pct = min(100.0, (used / total * 100.0) if total else 0.0)
            return used, total, pct
        return None

    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        try:
            text = meminfo.read_text(encoding="utf-8")
            vals: dict[str, int] = {}
            for line in text.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    num = v.strip().split()[0]
                    if num.isdigit():
                        vals[k.strip()] = int(num) * 1024
            total = vals.get("MemTotal", 0)
            avail = vals.get("MemAvailable", vals.get("MemFree", 0))
            if total > 0:
                used = max(0, total - avail)
                return used, total, (used / total * 100.0)
        except OSError:
            pass
    return None


def _get_battery_info() -> tuple[int, bool] | None:
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class SYSTEM_POWER_STATUS(ctypes.Structure):
                _fields_ = [
                    ("ACLineStatus", wintypes.BYTE),
                    ("BatteryFlag", wintypes.BYTE),
                    ("BatteryLifePercent", wintypes.BYTE),
                    ("SystemStatusFlag", wintypes.BYTE),
                    ("BatteryLifeTime", wintypes.DWORD),
                    ("BatteryFullLifeTime", wintypes.DWORD),
                ]

            ps = SYSTEM_POWER_STATUS()
            if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(ps)):
                if (ps.BatteryFlag & 128) or ps.BatteryLifePercent == 255:
                    return None
                return int(ps.BatteryLifePercent), ps.ACLineStatus == 1
        except Exception:
            return None

    if sys.platform == "darwin":
        out = _run_quick(["pmset", "-g", "batt"])
        match = re.search(r"(\d{1,3})%;\s*([^;]+);", out)
        if match:
            pct = int(match.group(1))
            state = match.group(2).lower()
            plugged = "ac" in out.lower() or "charging" in state or "charged" in state
            return pct, plugged
        return None

    supply_dir = Path("/sys/class/power_supply")
    if supply_dir.exists():
        for bat in sorted(supply_dir.glob("BAT*")):
            cap = bat / "capacity"
            st = bat / "status"
            if cap.exists():
                try:
                    pct = int(cap.read_text(encoding="utf-8").strip())
                    status_txt = st.read_text(encoding="utf-8").strip().lower() if st.exists() else ""
                    plugged = status_txt in ("charging", "full", "not charging")
                    return pct, plugged
                except (OSError, ValueError):
                    continue
    return None


def _get_disks() -> list[DiskStat]:
    targets: list[tuple[str, Path]] = []
    cwd = Path.cwd()
    home = Path.home()

    def root_key(p: Path) -> str:
        resolved = p.resolve()
        if resolved.drive:
            return resolved.drive.upper()
        return "/"

    seen: set[str] = set()
    for path in (cwd, home):
        try:
            key = root_key(path)
            if key in seen:
                continue
            seen.add(key)
            usage = shutil.disk_usage(path)
            pct = (usage.used / usage.total * 100.0) if usage.total else 0.0
            targets.append(
                DiskStat(
                    label=key,
                    used_bytes=usage.used,
                    total_bytes=usage.total,
                    free_bytes=usage.free,
                    percent=pct,
                )
            )
        except OSError:
            continue
    return targets


def _get_local_ip() -> str:
    try:
        host = socket.gethostname()
        for info in socket.getaddrinfo(host, None, socket.AF_INET):
            ip = str(info[4][0])
            if ip and not ip.startswith("127."):
                return ip
        resolved = socket.gethostbyname(host)
        if resolved:
            return resolved
    except OSError:
        pass
    return "127.0.0.1"


def gather_vitals() -> SystemVitals:
    """Gather offline system vitals safely across Windows, macOS, and Linux."""
    cores = os.cpu_count() or 1
    ram = _get_ram_info()
    batt = _get_battery_info()
    return SystemVitals(
        hostname=socket.gethostname(),
        os_label=_detect_os_label(),
        arch=platform.machine() or "unknown",
        shell=_detect_shell(),
        python_version=platform.python_version(),
        uptime=_get_uptime(),
        cpu_cores=cores,
        cpu_detail=_get_cpu_detail(cores),
        ram_used=ram[0] if ram else None,
        ram_total=ram[1] if ram else None,
        ram_percent=ram[2] if ram else None,
        disks=_get_disks(),
        battery_percent=batt[0] if batt else None,
        battery_plugged=batt[1] if batt else None,
        local_ip=_get_local_ip(),
    )


def format_vitals_report(vitals: SystemVitals, now: datetime | None = None) -> tuple[str, str, list[tuple[str, str]]]:
    """Turn SystemVitals into (mood, sirius_comment, table_rows)."""
    rows: list[tuple[str, str]] = [
        ("Host", f"{vitals.hostname} ({vitals.os_label} · {vitals.arch})"),
        ("Shell / Py", f"{vitals.shell} · Python {vitals.python_version}"),
        ("Uptime", vitals.uptime),
        ("CPU", vitals.cpu_detail),
    ]

    if vitals.ram_used is not None and vitals.ram_total is not None and vitals.ram_percent is not None:
        rows.append((
            "Memory",
            f"{_progress_bar(vitals.ram_percent)} {vitals.ram_percent:.0f}% "
            f"({format_bytes_human(vitals.ram_used)} / {format_bytes_human(vitals.ram_total)})",
        ))
    else:
        rows.append(("Memory", "n/a"))

    for disk in vitals.disks:
        rows.append((
            f"Disk ({disk.label})",
            f"{_progress_bar(disk.percent)} {disk.percent:.0f}% "
            f"({format_bytes_human(disk.free_bytes)} free of {format_bytes_human(disk.total_bytes)})",
        ))

    if vitals.battery_percent is not None:
        plug = "plugged in" if vitals.battery_plugged else "on battery"
        rows.append(("Battery", f"{_progress_bar(vitals.battery_percent)} {vitals.battery_percent}% ({plug})"))

    rows.append(("Local IP", vitals.local_ip))

    # Determine Sirius expression and sharp chill commentary
    worst_disk = max((d.percent for d in vitals.disks), default=0.0)
    ram_pct = vitals.ram_percent or 0.0
    low_batt = vitals.battery_percent is not None and not vitals.battery_plugged and vitals.battery_percent <= 20

    if worst_disk >= 92.0:
        mood = "alarmed"
        comment = f"Whoa dude—disk's slammed at {worst_disk:.0f}%! Sweep some dead weight before things get crispy."
    elif low_batt:
        mood = "alarmed"
        comment = f"Battery's down to {vitals.battery_percent}%, dude. Plug in before we both go dark!"
    elif ram_pct >= 88.0:
        mood = "unimpressed"
        comment = f"RAM's packed to {ram_pct:.0f}%, dude. Forty browser tabs open again or what?"
    elif worst_disk >= 80.0:
        mood = "curious"
        comment = f"Lookin' okay, though disk's creepin' up to {worst_disk:.0f}%, dude. Keep an eye on it."
    else:
        hour = (now or datetime.now()).hour
        if 0 <= hour < 5:
            mood = "smug"
            comment = "Rig's runnin' breezy, dude—unlike your sleep schedule at this hour."
        else:
            mood = "smug"
            comment = "System's hummin' smooth, dude. Plenty of headroom, zero drama."

    return mood, comment, rows
