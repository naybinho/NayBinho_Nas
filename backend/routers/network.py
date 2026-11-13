"""
NayBinho NAS — Network Router.

Endpoints:
  GET  /api/network/interfaces   — list network interfaces with IPs, speed, stats
  POST /api/network/configure    — configure an interface (IP, gateway, DNS)
  GET  /api/network/stats        — per-interface I/O counters
  GET  /api/network/firewall     — list UFW rules
  POST /api/network/firewall     — add UFW rule
  DELETE /api/network/firewall/{rule} — delete UFW rule by number
"""
from __future__ import annotations

import re
import socket
import subprocess
from typing import Any, Literal, Optional

import psutil
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from loguru import logger

from middleware.auth import decode_token

router = APIRouter(prefix="/network", tags=["Network"])
security = HTTPBearer()


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _require_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    payload = decode_token(credentials.credentials)
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return payload


def _require_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return decode_token(credentials.credentials)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _run(cmd: list[str], timeout: int = 20) -> tuple[int, str, str]:
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def _interface_speed(iface: str) -> Optional[int]:
    """Read link speed in Mbps from /sys/class/net/<iface>/speed."""
    try:
        path = f"/sys/class/net/{iface}/speed"
        return int(open(path).read().strip())
    except Exception:
        return None


def _get_dns() -> list[str]:
    """Parse /etc/resolv.conf for nameservers."""
    ns = []
    try:
        for line in open("/etc/resolv.conf"):
            line = line.strip()
            if line.startswith("nameserver"):
                parts = line.split()
                if len(parts) > 1:
                    ns.append(parts[1])
    except Exception:
        pass
    return ns


# ── Schemas ───────────────────────────────────────────────────────────────────

class InterfaceConfig(BaseModel):
    interface: str
    method: Literal["dhcp", "static"] = "dhcp"
    address: Optional[str] = None      # e.g. "192.168.1.100"
    netmask: Optional[str] = None      # e.g. "255.255.255.0"
    gateway: Optional[str] = None      # e.g. "192.168.1.1"
    dns: Optional[list[str]] = None    # e.g. ["8.8.8.8", "1.1.1.1"]


class FirewallRule(BaseModel):
    action: Literal["allow", "deny", "reject"] = "allow"
    direction: Literal["in", "out"] = "in"
    proto: Optional[Literal["tcp", "udp", "any"]] = "tcp"
    port: Optional[str] = None           # e.g. "80", "22:25", "443"
    from_ip: Optional[str] = None        # e.g. "192.168.1.0/24"
    to_ip: Optional[str] = None
    comment: Optional[str] = None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/interfaces")
async def list_interfaces(_: dict = Depends(_require_user)):
    """List all network interfaces with addresses, speed, and flags."""
    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()
    io = psutil.net_io_counters(pernic=True)

    result = []
    for name, addr_list in addrs.items():
        iface_stat = stats.get(name)
        iface_io = io.get(name)

        ipv4 = [
            {"address": a.address, "netmask": a.netmask, "broadcast": a.broadcast}
            for a in addr_list if a.family == socket.AF_INET
        ]
        ipv6 = [
            {"address": a.address, "netmask": a.netmask}
            for a in addr_list if a.family == socket.AF_INET6
        ]
        mac = next(
            (a.address for a in addr_list if a.family == psutil.AF_LINK), None
        )

        result.append({
            "name": name,
            "mac": mac,
            "ipv4": ipv4,
            "ipv6": ipv6,
            "speed_mbps": _interface_speed(name),
            "mtu": iface_stat.mtu if iface_stat else None,
            "is_up": iface_stat.isup if iface_stat else False,
            "duplex": iface_stat.duplex.name if iface_stat else None,
            "bytes_sent": iface_io.bytes_sent if iface_io else 0,
            "bytes_recv": iface_io.bytes_recv if iface_io else 0,
            "packets_sent": iface_io.packets_sent if iface_io else 0,
            "packets_recv": iface_io.packets_recv if iface_io else 0,
            "errin": iface_io.errin if iface_io else 0,
            "errout": iface_io.errout if iface_io else 0,
            "dropin": iface_io.dropin if iface_io else 0,
            "dropout": iface_io.dropout if iface_io else 0,
            "dns": _get_dns(),
        })
    return result


@router.post("/configure")
async def configure_interface(
    cfg: InterfaceConfig,
    _: dict = Depends(_require_admin),
):
    """Configure a network interface via nmcli or ip commands."""
    iface = cfg.interface

    if cfg.method == "dhcp":
        rc, out, err = _run(["nmcli", "device", "modify", iface,
                              "ipv4.method", "auto",
                              "ipv4.addresses", "",
                              "ipv4.gateway", "",
                              "ipv4.dns", ""])
        if rc != 0:
            # Fallback to dhclient
            _run(["dhclient", "-r", iface])
            rc, out, err = _run(["dhclient", iface])
            if rc != 0:
                raise HTTPException(status_code=500, detail=err)
    else:
        if not cfg.address or not cfg.netmask:
            raise HTTPException(
                status_code=400, detail="address and netmask required for static config"
            )
        cidr = f"{cfg.address}/{cfg.netmask}"
        cmd = [
            "nmcli", "device", "modify", iface,
            "ipv4.method", "manual",
            "ipv4.addresses", cidr,
        ]
        if cfg.gateway:
            cmd += ["ipv4.gateway", cfg.gateway]
        if cfg.dns:
            cmd += ["ipv4.dns", ",".join(cfg.dns)]
        rc, out, err = _run(cmd)
        if rc != 0:
            raise HTTPException(status_code=500, detail=err)

    _run(["nmcli", "device", "reapply", iface])
    return {"message": f"Interface {iface} configured ({cfg.method})", "stdout": out}


@router.get("/stats")
async def network_stats(_: dict = Depends(_require_user)):
    """Return per-interface and total I/O counters."""
    per_nic = psutil.net_io_counters(pernic=True)
    total = psutil.net_io_counters(pernic=False)
    return {
        "total": total._asdict(),
        "per_interface": {name: v._asdict() for name, v in per_nic.items()},
        "connections": len(psutil.net_connections(kind="inet")),
    }


# ── Firewall (UFW) ────────────────────────────────────────────────────────────

@router.get("/firewall")
async def list_firewall_rules(_: dict = Depends(_require_admin)):
    """List UFW rules (numbered)."""
    rc, out, err = _run(["ufw", "status", "numbered", "verbose"])
    if rc != 0:
        return {"status": "inactive", "rules": [], "raw": err}

    rules = []
    for line in out.splitlines():
        m = re.match(r"\[\s*(\d+)\]\s+(.+)", line)
        if m:
            rules.append({"number": int(m.group(1)), "rule": m.group(2).strip()})

    # Overall status
    status_line = next((l for l in out.splitlines() if "Status:" in l), "")
    status = "active" if "active" in status_line.lower() else "inactive"
    return {"status": status, "rules": rules, "raw": out}


@router.post("/firewall")
async def add_firewall_rule(
    rule: FirewallRule,
    _: dict = Depends(_require_admin),
):
    """Add a UFW rule."""
    cmd = ["ufw"]
    if rule.from_ip:
        cmd += ["from", rule.from_ip]
    if rule.to_ip:
        cmd += ["to", rule.to_ip]
    if rule.port:
        cmd += ["port", rule.port]
    if rule.proto and rule.proto != "any":
        cmd += ["proto", rule.proto]
    cmd += [rule.action]

    # Ensure UFW is enabled
    _run(["ufw", "--force", "enable"])
    rc, out, err = _run(cmd)
    if rc != 0:
        raise HTTPException(status_code=500, detail=err)
    return {"message": "Rule added", "stdout": out}


@router.delete("/firewall/{rule_number}")
async def delete_firewall_rule(
    rule_number: int,
    _: dict = Depends(_require_admin),
):
    """Delete a UFW rule by its number (from GET /firewall)."""
    rc, out, err = _run(["ufw", "--force", "delete", str(rule_number)])
    if rc != 0:
        raise HTTPException(status_code=500, detail=err)
    return {"message": f"Rule #{rule_number} deleted", "stdout": out}
