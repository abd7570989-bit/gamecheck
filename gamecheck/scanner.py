"""Read this computer's specs. Entirely local: no network access of any kind.

On Windows everything comes from the registry and kernel32 (no PowerShell or WMI),
which is fast and works without admin rights. Linux and macOS are supported for
development and as a best effort.
"""

import os
import platform
import re
import shutil
import subprocess
import sys

GB = 1024 ** 3


def _run(cmd, timeout=5):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        return out.stdout if out.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


# ---------------------------------------------------------------- Windows

def _win_reg_value(root, path, name):
    import winreg
    try:
        with winreg.OpenKey(root, path) as key:
            return winreg.QueryValueEx(key, name)[0]
    except OSError:
        return None


def _win_cpu():
    import winreg
    name = _win_reg_value(winreg.HKEY_LOCAL_MACHINE,
                          r"HARDWARE\DESCRIPTION\System\CentralProcessor\0", "ProcessorNameString")
    return (name or platform.processor() or "").strip()


def _win_ram_gb():
    import ctypes
    kb = ctypes.c_ulonglong(0)
    # Installed physical memory (what the user bought), not memory usable by Windows.
    if ctypes.windll.kernel32.GetPhysicallyInstalledSystemMemory(ctypes.byref(kb)) and kb.value:
        return kb.value / (1024 ** 2)

    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]

    status = MEMORYSTATUSEX()
    status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
    if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return status.ullTotalPhys / GB
    return None


_SKIP_ADAPTERS = re.compile(r"basic display|basic render|remote|virtual|parsec|mirage|dameware|citrix", re.I)


def _registry_vram_gb(value):
    if isinstance(value, int) and value > 0:
        return value / GB
    if isinstance(value, bytes) and value:
        return int.from_bytes(value[:8], "little") / GB
    return None


def _win_gpus():
    import winreg
    gpus = []
    base = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base) as cls:
            index = 0
            while True:
                try:
                    sub = winreg.EnumKey(cls, index)
                except OSError:
                    break
                index += 1
                if not sub.isdigit():
                    continue
                path = base + "\\" + sub
                name = _win_reg_value(winreg.HKEY_LOCAL_MACHINE, path, "DriverDesc")
                if not name or _SKIP_ADAPTERS.search(name):
                    continue
                # qwMemorySize is 64-bit; the older MemorySize value tops out at 4 GB.
                vram = _registry_vram_gb(_win_reg_value(winreg.HKEY_LOCAL_MACHINE, path,
                                                        "HardwareInformation.qwMemorySize"))
                if vram is None:
                    vram = _registry_vram_gb(_win_reg_value(winreg.HKEY_LOCAL_MACHINE, path,
                                                            "HardwareInformation.MemorySize"))
                if not any(g["name"] == name for g in gpus):
                    gpus.append({"name": name.strip(), "vram_gb": vram})
    except OSError:
        pass
    if not gpus:
        gpus = _win_display_devices()
    return gpus


def _win_display_devices():
    import ctypes
    from ctypes import wintypes

    class DISPLAY_DEVICEW(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("DeviceName", wintypes.WCHAR * 32),
                    ("DeviceString", wintypes.WCHAR * 128), ("StateFlags", wintypes.DWORD),
                    ("DeviceID", wintypes.WCHAR * 128), ("DeviceKey", wintypes.WCHAR * 128)]

    names = []
    device = DISPLAY_DEVICEW()
    device.cb = ctypes.sizeof(device)
    i = 0
    while ctypes.windll.user32.EnumDisplayDevicesW(None, i, ctypes.byref(device), 0):
        name = device.DeviceString.strip()
        if name and name not in names and not _SKIP_ADAPTERS.search(name):
            names.append(name)
        i += 1
    return [{"name": n, "vram_gb": None} for n in names]


def _win_os():
    ver = sys.getwindowsversion()
    major = ver.major
    # Windows 11 still reports 10.0; the build number tells them apart.
    if major == 10 and ver.build >= 22000:
        major = 11
    machine = (os.environ.get("PROCESSOR_ARCHITEW6432") or os.environ.get("PROCESSOR_ARCHITECTURE")
               or platform.machine()).upper()
    return {"family": "windows", "name": f"Windows {major}", "version": major,
            "build": ver.build, "is_64bit": machine in ("AMD64", "ARM64", "X86_64")}


def _win_disks():
    import ctypes
    disks = []
    mask = ctypes.windll.kernel32.GetLogicalDrives()
    for i in range(26):
        if not mask & (1 << i):
            continue
        root = f"{chr(65 + i)}:\\"
        if ctypes.windll.kernel32.GetDriveTypeW(root) != 3:  # DRIVE_FIXED only
            continue
        try:
            usage = shutil.disk_usage(root)
        except OSError:
            continue
        disks.append({"mount": root, "free_gb": usage.free / GB, "total_gb": usage.total / GB})
    return disks


# ---------------------------------------------------------------- Linux

def _linux_cpu():
    try:
        with open("/proc/cpuinfo", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                if line.lower().startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor()


def _linux_ram_gb():
    try:
        with open("/proc/meminfo", encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("MemTotal:"):
                    return int(line.split()[1]) / (1024 ** 2)
    except (OSError, ValueError):
        pass
    return None


def _linux_gpus():
    gpus = []
    for line in _run(["lspci", "-mm"]).splitlines():
        parts = re.findall(r'"([^"]*)"', line)
        if len(parts) >= 3 and re.search(r"VGA|3D|Display", parts[0]):
            name = parts[2]
            bracket = re.search(r"\[([^\]]+)\]", name)
            vendor = parts[1].split()[0]
            gpus.append({"name": f"{vendor} {bracket.group(1) if bracket else name}", "vram_gb": None})
    return gpus


def _posix_disks():
    disks = []
    for mount in ("/", os.path.expanduser("~")):
        try:
            usage = shutil.disk_usage(mount)
        except OSError:
            continue
        if not any(abs(d["total_gb"] - usage.total / GB) < 0.01 and abs(d["free_gb"] - usage.free / GB) < 0.01
                   for d in disks):
            disks.append({"mount": mount, "free_gb": usage.free / GB, "total_gb": usage.total / GB})
    return disks


def _mac_info():
    cpu = _run(["sysctl", "-n", "machdep.cpu.brand_string"]).strip()
    mem = _run(["sysctl", "-n", "hw.memsize"]).strip()
    gpus = [{"name": m.strip(), "vram_gb": None}
            for m in re.findall(r"Chipset Model:\s*(.+)", _run(["system_profiler", "SPDisplaysDataType"], 15))]
    return cpu, (int(mem) / GB if mem.isdigit() else None), gpus


# ---------------------------------------------------------------- public

def scan() -> dict:
    """Return a dict describing this computer. Missing pieces are None/empty, never fake."""
    errors = []

    def attempt(label, func, default):
        try:
            return func()
        except Exception as exc:  # a broken probe must not stop the rest of the scan
            errors.append(f"{label}: {exc}")
            return default

    if sys.platform == "win32":
        cpu = attempt("cpu", _win_cpu, "")
        ram = attempt("ram", _win_ram_gb, None)
        gpus = attempt("gpu", _win_gpus, [])
        os_info = attempt("os", _win_os, {"family": "windows", "name": "Windows", "version": None, "is_64bit": None})
        disks = attempt("disk", _win_disks, [])
    elif sys.platform == "darwin":
        cpu, ram, gpus = attempt("system", _mac_info, ("", None, []))
        os_info = {"family": "macos", "name": f"macOS {platform.mac_ver()[0]}", "version": None,
                   "is_64bit": sys.maxsize > 2 ** 32}
        disks = attempt("disk", _posix_disks, [])
    else:
        cpu = attempt("cpu", _linux_cpu, "")
        ram = attempt("ram", _linux_ram_gb, None)
        gpus = attempt("gpu", _linux_gpus, [])
        os_info = {"family": "linux", "name": f"Linux {platform.release()}", "version": None,
                   "is_64bit": sys.maxsize > 2 ** 32}
        disks = attempt("disk", _posix_disks, [])

    return {
        "os": os_info,
        "cpu": {"name": cpu or "", "threads": os.cpu_count()},
        "ram_gb": round(ram, 2) if ram else None,
        "gpus": gpus,
        "disks": [dict(d, free_gb=round(d["free_gb"], 1), total_gb=round(d["total_gb"], 1)) for d in disks],
        "errors": errors,
    }
