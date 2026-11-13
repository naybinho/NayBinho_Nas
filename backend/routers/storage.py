"""
NayBinho NAS — Storage Router.

Endpoints:
  GET  /api/storage/disks              — list physical disks with SMART / temp
  GET  /api/storage/raid               — list all md arrays
  POST /api/storage/raid/create        — create a new RAID array
  DELETE /api/storage/raid/{name}      — destroy a RAID array
  GET  /api/storage/smart/{device}     — full SMART report for a device
  GET  /api/storage/volumes            — list mounted volumes (ZFS + ext4 + other)
  POST /api/storage/volumes/format     — format a disk with a filesystem
  GET  /api/storage/shares             — list NFS/SMB shares
  POST /api/storage/shares             — add a share
  DELETE /api/storage/shares/{name}    — remove a share
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any, Literal, Optional

import psutil
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from loguru import logger

from middleware.auth import decode_token
from services import raid_service
from config import settings

router = APIRouter(prefix="/storage", tags=["Storage"])
security = HTTPBearer()

SHARES_PATH = settings.shares_config_path


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _require_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    payload = decode_token(credentials.credentials)
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return payload


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def _lsblk() -> list[dict[str, Any]]:
    """Return lsblk -Jbo output parsed as a list of block devices."""
    rc, out, err = _run(
        ["lsblk", "-Jbo",
         "NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,VENDOR,MODEL,SERIAL,ROTA,TRAN,HOTPLUG,STATE"],
        timeout=15,
    )
    if rc != 0:
        logger.warning(f"lsblk failed: {err}")
        return []
    try:
        data = json.loads(out)
        return data.get("blockdevices", [])
    except json.JSONDecodeError:
        return []


def _smart_short(device: str) -> dict[str, Any]:
    """Run smartctl -A and return parsed attributes."""
    rc, out, _ = _run(["smartctl", "-A", "-j", f"/dev/{device}"], timeout=20)
    try:
        return json.loads(out)
    except Exception:
        return {}


def _disk_temp(device: str) -> Optional[float]:
    """Extract temperature from smartctl JSON."""
    data = _smart_short(device)
    # NVMe
    temp = data.get("temperature", {}).get("current")
    if temp is not None:
        return float(temp)
    # ATA SMART attributes
    for attr in data.get("ata_smart_attributes", {}).get("table", []):
        if attr.get("name") in ("Temperature_Celsius", "Airflow_Temperature_Cel"):
            return float(attr["value"])
    return None


def _load_shares() -> dict[str, Any]:
    try:
        return json.loads(Path(SHARES_PATH).read_text())
    except Exception:
        return {"smb": [], "nfs": []}


def _save_shares(data: dict):
    try:
        Path(SHARES_PATH).parent.mkdir(parents=True, exist_ok=True)
        Path(SHARES_PATH).write_text(json.dumps(data, indent=2))
    except Exception as exc:
        logger.error(f"Failed to save shares config: {exc}")


def _zfs_list() -> list[dict[str, Any]]:
    rc, out, _ = _run(["zfs", "list", "-Hp", "-o",
                        "name,used,available,referenced,mountpoint,type"], timeout=15)
    if rc != 0:
        return []
    datasets = []
    for line in out.strip().splitlines():
        parts = line.split("\t")
        if len(parts) >= 6:
            datasets.append({
                "name": parts[0],
                "used": int(parts[1]),
                "available": int(parts[2]),
                "referenced": int(parts[3]),
                "mountpoint": parts[4],
                "type": parts[5],
                "filesystem": "zfs",
            })
    return datasets


# ── Schemas ───────────────────────────────────────────────────────────────────

class RaidCreateRequest(BaseModel):
    name: str                   # e.g. "md0"
    level: int                  # 0, 1, 4, 5, 6, 10
    devices: list[str]          # e.g. ["/dev/sdb", "/dev/sdc"]
    spare_devices: int = 0
    chunk_kb: int = 512


class FormatRequest(BaseModel):
    device: str                 # e.g. "/dev/sdb"
    filesystem: Literal["ext4", "xfs", "btrfs", "ntfs", "fat32"] = "ext4"
    label: Optional[str] = None
    force: bool = False


class ShareCreateRequest(BaseModel):
    protocol: Literal["smb", "nfs"]
    name: str
    path: str
    comment: Optional[str] = ""
    read_only: bool = False
    allowed_hosts: Optional[str] = "*"


class ShareDeleteRequest(BaseModel):
    protocol: Literal["smb", "nfs"]


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/disks")
async def list_disks():
    """List all physical disks with model, serial, size, SMART temp."""
    devices = _lsblk()
    result = []
    for dev in devices:
        if dev.get("type") not in ("disk",):
            continue
        name = dev["name"]
        temp = None
        smart_ok = None
        try:
            temp = _disk_temp(name)
            rc, out, _ = _run(["smartctl", "-H", f"/dev/{name}"], timeout=15)
            smart_ok = "PASSED" in out or "OK" in out
        except Exception:
            pass

        result.append({
            "name": name,
            "device": f"/dev/{name}",
            "size_bytes": dev.get("size", 0),
            "model": (dev.get("model") or "").strip(),
            "vendor": (dev.get("vendor") or "").strip(),
            "serial": (dev.get("serial") or "").strip(),
            "transport": dev.get("tran", ""),
            "rotational": bool(dev.get("rota", True)),
            "hotplug": bool(dev.get("hotplug", False)),
            "state": dev.get("state", ""),
            "filesystem": dev.get("fstype", ""),
            "mountpoint": dev.get("mountpoint", ""),
            "temperature_celsius": temp,
            "smart_passed": smart_ok,
            "children": dev.get("children", []),
        })
    return result


@router.get("/raid")
async def list_raid():
    """List all Linux software RAID arrays (/proc/mdstat)."""
    arrays = raid_service.parse_mdstat()
    # Enrich with fault tolerance
    for arr in arrays:
        level = arr.get("level", "")
        n_devs = arr.get("total_devices", 0)
        arr["fault_tolerance"] = raid_service.fault_tolerance(level, n_devs)
    return arrays


@router.post("/raid/create", status_code=201)
async def create_raid(
    req: RaidCreateRequest,
    _: dict = Depends(_require_admin),
):
    """Create a new mdadm RAID array."""
    result = raid_service.create_raid(
        name=req.name,
        level=req.level,
        devices=req.devices,
        spare_devices=req.spare_devices,
        chunk_kb=req.chunk_kb,
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "mdadm failed"))
    return result


@router.delete("/raid/{name}")
async def delete_raid(name: str, _: dict = Depends(_require_admin)):
    """Stop and destroy a RAID array."""
    result = raid_service.remove_raid(name)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    return result


@router.get("/smart/{device}")
async def smart_report(device: str):
    """Return full smartctl JSON report for a device."""
    rc, out, err = _run(["smartctl", "-a", "-j", f"/dev/{device}"], timeout=30)
    try:
        data = json.loads(out)
    except Exception:
        data = {"raw": out, "error": err}
    if rc > 1:
        raise HTTPException(status_code=500, detail=f"smartctl error: {err}")
    return data


@router.get("/volumes")
async def list_volumes():
    """List all mounted volumes (ext4, xfs, btrfs, ZFS datasets)."""
    # psutil disk partitions
    partitions = []
    for p in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(p.mountpoint)
            partitions.append({
                "device": p.device,
                "mountpoint": p.mountpoint,
                "filesystem": p.fstype,
                "total_bytes": usage.total,
                "used_bytes": usage.used,
                "free_bytes": usage.free,
                "percent": usage.percent,
                "source": "system",
            })
        except Exception:
            pass

    # ZFS datasets
    zfs = _zfs_list()
    for ds in zfs:
        partitions.append({**ds, "source": "zfs"})

    return partitions


@router.post("/volumes/format", status_code=202)
async def format_volume(
    req: FormatRequest,
    _: dict = Depends(_require_admin),
):
    """Format a block device with the requested filesystem."""
    dev = req.device
    if not Path(dev).exists():
        raise HTTPException(status_code=404, detail=f"Device {dev} not found")

    if req.filesystem == "ext4":
        cmd = ["mkfs.ext4"]
        if req.force:
            cmd.append("-F")
        if req.label:
            cmd += ["-L", req.label]
        cmd.append(dev)
    elif req.filesystem == "xfs":
        cmd = ["mkfs.xfs"]
        if req.force:
            cmd.append("-f")
        if req.label:
            cmd += ["-L", req.label]
        cmd.append(dev)
    elif req.filesystem == "btrfs":
        cmd = ["mkfs.btrfs"]
        if req.force:
            cmd.append("-f")
        if req.label:
            cmd += ["-L", req.label]
        cmd.append(dev)
    elif req.filesystem == "ntfs":
        cmd = ["mkfs.ntfs", "--fast"]
        if req.label:
            cmd += ["-L", req.label]
        cmd.append(dev)
    elif req.filesystem == "fat32":
        cmd = ["mkfs.fat", "-F", "32"]
        if req.label:
            cmd += ["-n", req.label[:11].upper()]
        cmd.append(dev)
    else:
        raise HTTPException(status_code=400, detail="Unsupported filesystem")

    rc, out, err = _run(cmd, timeout=300)
    if rc != 0:
        raise HTTPException(status_code=500, detail=err)
    return {"message": f"Formatted {dev} as {req.filesystem}", "stdout": out}


@router.get("/shares")
async def list_shares():
    """Return NFS and SMB share configuration."""
    return _load_shares()


@router.post("/shares", status_code=201)
async def add_share(
    req: ShareCreateRequest,
    _: dict = Depends(_require_admin),
):
    """Add a new share to the configuration and reload the daemon."""
    shares = _load_shares()
    proto = req.protocol

    # Check duplicates
    if any(s["name"] == req.name for s in shares.get(proto, [])):
        raise HTTPException(status_code=409, detail=f"Share '{req.name}' already exists")

    entry = req.model_dump()
    shares.setdefault(proto, []).append(entry)
    _save_shares(shares)

    # Reload service
    if proto == "smb":
        _run(["smbcontrol", "smbd", "reload-config"])
    else:
        _run(["exportfs", "-ra"])

    return entry


@router.delete("/shares/{name}")
async def delete_share(
    name: str,
    protocol: Literal["smb", "nfs"] = "smb",
    _: dict = Depends(_require_admin),
):
    """Remove a share by name."""
    shares = _load_shares()
    proto_list = shares.get(protocol, [])
    new_list = [s for s in proto_list if s["name"] != name]
    if len(new_list) == len(proto_list):
        raise HTTPException(status_code=404, detail=f"Share '{name}' not found")
    shares[protocol] = new_list
    _save_shares(shares)

    if protocol == "smb":
        _run(["smbcontrol", "smbd", "reload-config"])
    else:
        _run(["exportfs", "-ra"])

    return {"message": f"Share '{name}' removed"}
