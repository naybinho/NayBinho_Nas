"""
NayBinho NAS — System Router.

Endpoints:
  GET  /api/system/info      — hostname, uptime, CPU, RAM, temperatures
  GET  /api/system/stats     — real-time metrics
  POST /api/system/reboot    — reboot the host
  POST /api/system/shutdown  — shutdown the host
  GET  /api/system/update    — check for available OS updates
  POST /api/system/update    — apply OS updates
  GET  /api/system/hostname  — get current hostname
  POST /api/system/hostname  — set hostname
"""
from __future__ import annotations

import asyncio
import platform
import subprocess
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import psutil
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel

from middleware.auth import decode_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from services.update_service import update_service

router = APIRouter(prefix="/system", tags=["System"])
security = HTTPBearer()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _require_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    payload = decode_token(credentials.credentials)
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return payload


def _run(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return result.returncode, result.stdout, result.stderr


def _uptime_seconds() -> float:
    return time.time() - psutil.boot_time()


def _uptime_human(seconds: float) -> str:
    td = timedelta(seconds=int(seconds))
    days = td.days
    hours, rem = divmod(td.seconds, 3600)
    minutes, secs = divmod(rem, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    parts.append(f"{minutes}m {secs}s")
    return " ".join(parts)


def _cpu_temps() -> dict[str, Any]:
    temps: dict[str, Any] = {}
    try:
        raw = psutil.sensors_temperatures()
        for key, entries in raw.items():
            temps[key] = [
                {"label": e.label or key, "current": e.current,
                 "high": e.high, "critical": e.critical}
                for e in entries
            ]
    except (AttributeError, NotImplementedError):
        pass
    return temps


def _memory_info() -> dict[str, Any]:
    vm = psutil.virtual_memory()
    sw = psutil.swap_memory()
    return {
        "total": vm.total,
        "available": vm.available,
        "used": vm.used,
        "percent": vm.percent,
        "swap_total": sw.total,
        "swap_used": sw.used,
        "swap_percent": sw.percent,
    }


# ── Schemas ───────────────────────────────────────────────────────────────────

class HostnameUpdate(BaseModel):
    hostname: str

class UpdateAction(BaseModel):
    apply: bool = False


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/info")
async def system_info():
    """Full system snapshot: hostname, uptime, CPU, RAM, temperatures."""
    uptime_s = _uptime_seconds()
    cpu_freq = psutil.cpu_freq()
    return {
        "hostname": platform.node(),
        "os": f"{platform.system()} {platform.release()}",
        "kernel": platform.version(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "boot_time": datetime.fromtimestamp(psutil.boot_time(), tz=timezone.utc).isoformat(),
        "uptime_seconds": uptime_s,
        "uptime_human": _uptime_human(uptime_s),
        "cpu": {
            "physical_cores": psutil.cpu_count(logical=False),
            "logical_cores": psutil.cpu_count(logical=True),
            "percent": psutil.cpu_percent(interval=0.5),
            "per_cpu": psutil.cpu_percent(interval=0.1, percpu=True),
            "frequency_mhz": {
                "current": cpu_freq.current if cpu_freq else None,
                "min": cpu_freq.min if cpu_freq else None,
                "max": cpu_freq.max if cpu_freq else None,
            },
            "load_avg": list(psutil.getloadavg()) if hasattr(psutil, "getloadavg") else [],
        },
        "memory": _memory_info(),
        "temperatures": _cpu_temps(),
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }


@router.get("/stats")
async def system_stats():
    """Lightweight real-time metrics for dashboard polling."""
    net = psutil.net_io_counters()
    disk_io = psutil.disk_io_counters()
    return {
        "cpu_percent": psutil.cpu_percent(interval=0.2),
        "memory_percent": psutil.virtual_memory().percent,
        "swap_percent": psutil.swap_memory().percent,
        "net_bytes_sent": net.bytes_sent,
        "net_bytes_recv": net.bytes_recv,
        "disk_read_bytes": disk_io.read_bytes if disk_io else 0,
        "disk_write_bytes": disk_io.write_bytes if disk_io else 0,
        "uptime_seconds": _uptime_seconds(),
        "temperatures": _cpu_temps(),
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
    }


@router.post("/reboot")
async def reboot_system(
    background_tasks: BackgroundTasks,
    _: dict = Depends(_require_admin),
):
    """Schedule a system reboot (5-second delay)."""
    def _do_reboot():
        time.sleep(5)
        subprocess.run(["reboot"], check=False)

    background_tasks.add_task(_do_reboot)
    return {"message": "System will reboot in 5 seconds"}


@router.post("/shutdown")
async def shutdown_system(
    background_tasks: BackgroundTasks,
    _: dict = Depends(_require_admin),
):
    """Schedule a system shutdown (5-second delay)."""
    def _do_shutdown():
        time.sleep(5)
        subprocess.run(["shutdown", "-h", "now"], check=False)

    background_tasks.add_task(_do_shutdown)
    return {"message": "System will shut down in 5 seconds"}


@router.get("/update")
@router.get("/update/check")
async def check_updates(_: dict = Depends(_require_admin)):
    """Verifica se há nova versão da ISO ou pacote no GitHub Releases e pacotes APT."""
    info = await update_service.check_updates()
    return info


@router.get("/update/status")
async def get_update_status(_: dict = Depends(_require_admin)):
    """Retorna o progresso atual do processo de auto-atualização em segundo plano."""
    return update_service.get_status()


@router.post("/update")
@router.post("/update/apply")
async def apply_updates(
    action: Optional[UpdateAction] = None,
    _: dict = Depends(_require_admin),
):
    """Dispara a auto-atualização do sistema NayBinho NAS e/ou pacotes do SO."""
    res = await update_service.apply_self_update(
        update_os_packages=True,
        update_nas_software=True,
    )
    return res


@router.get("/hostname")
async def get_hostname():
    """Return the current hostname."""
    return {"hostname": platform.node()}


@router.post("/hostname")
async def set_hostname(
    body: HostnameUpdate,
    _: dict = Depends(_require_admin),
):
    """Set a new hostname using hostnamectl."""
    name = body.hostname.strip()
    if not name or len(name) > 63:
        raise HTTPException(status_code=400, detail="Invalid hostname")

    rc, _, err = _run(["hostnamectl", "set-hostname", name])
    if rc != 0:
        raise HTTPException(status_code=500, detail=f"hostnamectl failed: {err}")
    return {"hostname": name, "message": "Hostname updated successfully"}
