"""
NayBinho NAS — RAID Service
Complete service for managing Linux Software RAID (mdadm).

Supports RAID levels 0, 1, 5, 6, 10.
Reads /proc/mdstat for real-time status and delegates creation/destruction
to mdadm subprocess calls (requires root / sudo).
"""

from __future__ import annotations

import logging
import re
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from backend.models.storage_models import (
    OperationResult,
    RaidAddSpareRequest,
    RaidArray,
    RaidCreateRequest,
    RaidLevel,
    RaidMember,
    RaidResyncInfo,
    RaidState,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MDSTAT_PATH = "/proc/mdstat"
MDADM_BIN = "/sbin/mdadm"

RAID_FAULT_TOLERANCE: Dict[int, str] = {
    0: "0 discos (sem tolerância a falhas)",
    1: "1 disco (qualquer membro)",
    5: "1 disco",
    6: "2 discos",
    10: "N/2 discos (metade do array)",
}

RAID_MIN_DISKS: Dict[int, int] = {
    0: 2,
    1: 2,
    5: 3,
    6: 4,
    10: 4,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a shell command and return the CompletedProcess result."""
    logger.debug("Running: %s", " ".join(cmd))
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=check,
    )


def _bytes_from_kb(kb: int) -> int:
    return kb * 1024


def _bytes_from_block(blocks: int, block_size: int = 512) -> int:
    return blocks * block_size


# ---------------------------------------------------------------------------
# /proc/mdstat Parser
# ---------------------------------------------------------------------------

class MdstatParser:
    """Parse /proc/mdstat into structured data."""

    # md0 : active raid5 sdb[0] sdc[1] sdd[2]
    _ARRAY_LINE = re.compile(
        r"^(md\d+)\s*:\s*(\w+)\s+raid(\d+)\s+(.+)$"
    )
    # 1953381888 blocks super 1.2 level 5, 512k chunk, algorithm 2 [3/3] [UUU]
    _BLOCKS_LINE = re.compile(
        r"^\s*(\d+)\s+blocks\s+(.+)\[(\d+)/(\d+)\]\s+\[([U_]+)\]"
    )
    # [=>...................]  resync = 1.0% (20480/1953381888) finish=...
    _RESYNC_LINE = re.compile(
        r"^\s*\[.*?\]\s+(\w+)\s*=\s*([\d.]+)%\s+\((\d+)/(\d+)\)"
        r"(?:\s+finish=([\d.]+)min)?"
        r"(?:\s+speed=(\d+)K/sec)?"
    )
    # Member device pattern:  sdb[0]  or  sdc[1](S) or sdd[2](F)
    _MEMBER_RE = re.compile(r"(\w+)\[(\d+)\](\(S\)|\(F\))?")

    @classmethod
    def parse(cls, content: Optional[str] = None) -> List[RaidArray]:
        if content is None:
            try:
                content = Path(MDSTAT_PATH).read_text()
            except FileNotFoundError:
                logger.warning("%s not found (not running on Linux?)", MDSTAT_PATH)
                return []

        arrays: List[RaidArray] = []
        lines = content.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            m = cls._ARRAY_LINE.match(line)
            if m:
                name, status_str, level_str, members_str = m.groups()
                array = cls._build_array(
                    name, status_str, int(level_str), members_str
                )
                # Next line: blocks info
                if i + 1 < len(lines):
                    bm = cls._BLOCKS_LINE.match(lines[i + 1])
                    if bm:
                        blocks_str, meta, total, active, bitmap = bm.groups()
                        array.size_bytes = _bytes_from_block(int(blocks_str))
                        array.total_devices = int(total)
                        array.active_devices = int(active)
                        array.usable_bytes = cls._calc_usable(
                            array.level, array.size_bytes, array.total_devices
                        )
                        # Count U/_ in bitmap
                        failed = bitmap.count("_")
                        array.failed_devices = failed
                        if failed > 0 and array.state == RaidState.ACTIVE:
                            array.state = RaidState.DEGRADED
                # Next line: resync info
                if i + 2 < len(lines):
                    rm = cls._RESYNC_LINE.match(lines[i + 2])
                    if rm:
                        action, pct, done, total, finish_min, speed = rm.groups()
                        array.resync = RaidResyncInfo(
                            action=action,
                            progress_pct=float(pct),
                            speed_kbps=int(speed) if speed else None,
                            estimated_finish=f"{finish_min} min" if finish_min else None,
                            blocks_done=int(done),
                            blocks_total=int(total),
                        )
                        if action in ("resync", "recovery"):
                            array.state = RaidState.RESYNCING
                arrays.append(array)
            i += 1
        return arrays

    @classmethod
    def _build_array(
        cls, name: str, status_str: str, level_int: int, members_str: str
    ) -> RaidArray:
        try:
            level = RaidLevel(level_int)
        except ValueError:
            level = RaidLevel.RAID0

        state = {
            "active": RaidState.ACTIVE,
            "inactive": RaidState.INACTIVE,
            "degraded": RaidState.DEGRADED,
        }.get(status_str, RaidState.UNKNOWN)

        members: List[RaidMember] = []
        spare_count = 0
        for mm in cls._MEMBER_RE.finditer(members_str):
            dev, slot, flag = mm.groups()
            is_faulty = flag == "(F)"
            is_spare = flag == "(S)"
            if is_spare:
                spare_count += 1
            role = "faulty" if is_faulty else ("spare" if is_spare else "active sync")
            members.append(
                RaidMember(
                    device=f"/dev/{dev}",
                    role=role,
                    state="faulty" if is_faulty else "in_sync",
                    slot=int(slot),
                    is_faulty=is_faulty,
                    is_spare=is_spare,
                )
            )

        tolerance = {0: 0, 1: 1, 5: 1, 6: 2, 10: len(members) // 2}.get(level_int, 0)

        return RaidArray(
            name=name,
            path=f"/dev/{name}",
            level=level,
            state=state,
            members=members,
            spare_devices=spare_count,
            fault_tolerance=tolerance,
            description=RAID_FAULT_TOLERANCE.get(level_int, ""),
        )

    @staticmethod
    def _calc_usable(level: RaidLevel, size_bytes: int, n_devices: int) -> int:
        """Return usable capacity in bytes given array total size and disk count."""
        return size_bytes


# ---------------------------------------------------------------------------
# RAID Capacity Calculator
# ---------------------------------------------------------------------------

def calculate_capacity(
    level: RaidLevel, disk_size_bytes: int, num_disks: int
) -> Tuple[int, int, str]:
    """
    Calculate usable capacity for a given RAID level.

    Returns (usable_bytes, fault_tolerance_disks, formula_description).
    """
    n = num_disks
    s = disk_size_bytes

    if level == RaidLevel.RAID0:
        usable = n * s
        tolerance = 0
        formula = f"RAID 0: {n} x {s} = {usable} bytes (sem redundancia)"
    elif level == RaidLevel.RAID1:
        usable = s
        tolerance = n - 1
        formula = f"RAID 1: 1 x {s} = {usable} bytes (espelho; pode perder {tolerance} disco(s))"
    elif level == RaidLevel.RAID5:
        usable = (n - 1) * s
        tolerance = 1
        formula = f"RAID 5: ({n}-1) x {s} = {usable} bytes (1 paridade; pode perder 1 disco)"
    elif level == RaidLevel.RAID6:
        usable = (n - 2) * s
        tolerance = 2
        formula = f"RAID 6: ({n}-2) x {s} = {usable} bytes (2 paridades; pode perder 2 discos)"
    elif level == RaidLevel.RAID10:
        usable = (n // 2) * s
        tolerance = n // 2
        formula = (
            f"RAID 10: ({n}/2) x {s} = {usable} bytes "
            f"(mirror+stripe; pode perder ate {tolerance} disco(s))"
        )
    else:
        usable = 0
        tolerance = 0
        formula = "Nivel RAID desconhecido"

    return usable, tolerance, formula


# ---------------------------------------------------------------------------
# RAID Service
# ---------------------------------------------------------------------------

class RaidService:
    """
    High-level service for managing Linux Software RAID arrays via mdadm.

    All write operations require the process to run as root (or with sudo).
    """

    def __init__(self, mdadm_bin: str = MDADM_BIN):
        self.mdadm_bin = mdadm_bin

    # ------------------------------------------------------------------
    # Read / Status
    # ------------------------------------------------------------------

    def list_arrays(self) -> List[RaidArray]:
        """Return all RAID arrays parsed from /proc/mdstat."""
        arrays = MdstatParser.parse()
        for array in arrays:
            self._enrich_with_detail(array)
        return arrays

    def get_array(self, name: str) -> Optional[RaidArray]:
        """Get a single array by md device name (e.g. 'md0')."""
        arrays = self.list_arrays()
        for arr in arrays:
            if arr.name == name:
                return arr
        return None

    def _enrich_with_detail(self, array: RaidArray) -> None:
        """Run `mdadm --detail /dev/mdX` and fill extra fields."""
        try:
            result = _run([self.mdadm_bin, "--detail", array.path], check=False)
            if result.returncode != 0:
                return
            output = result.stdout

            uuid_m = re.search(r"UUID\s*:\s*(\S+)", output)
            if uuid_m:
                array.uuid = uuid_m.group(1)

            chunk_m = re.search(r"Chunk Size\s*:\s*(\d+)K", output)
            if chunk_m:
                array.chunk_size_kb = int(chunk_m.group(1))

            meta_m = re.search(r"Version\s*:\s*(\S+)", output)
            if meta_m:
                array.metadata_version = meta_m.group(1)

        except Exception as exc:
            logger.warning("Could not enrich %s: %s", array.name, exc)

    def get_resync_progress(self, name: str) -> Optional[RaidResyncInfo]:
        """Return current resync/rebuild progress for an array."""
        array = self.get_array(name)
        return array.resync if array else None

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    def create_array(self, req: RaidCreateRequest) -> OperationResult:
        """Create a new RAID array."""
        level = req.level.value
        min_disks = RAID_MIN_DISKS.get(level, 2)

        if len(req.devices) < min_disks:
            return OperationResult(
                success=False,
                message=(
                    f"RAID {level} requer no minimo {min_disks} dispositivos; "
                    f"fornecidos: {len(req.devices)}"
                ),
            )

        md_path = f"/dev/{req.name}"
        all_devices = req.devices + req.spare_devices

        cmd = [
            self.mdadm_bin,
            "--create",
            md_path,
            "--level", str(level),
            "--raid-devices", str(len(req.devices)),
            "--metadata", req.metadata_version,
            "--chunk", str(req.chunk_size_kb),
            "--run",
        ]

        if req.spare_devices:
            cmd += ["--spare-devices", str(len(req.spare_devices))]

        cmd += all_devices

        logger.info("Creating RAID %d array %s with devices %s", level, req.name, all_devices)

        try:
            result = _run(cmd, check=False)
            if result.returncode != 0:
                return OperationResult(
                    success=False,
                    message=f"Falha ao criar array {req.name}",
                    error=result.stderr,
                )

            self._save_mdadm_conf()

            usable, tolerance, formula = calculate_capacity(
                req.level, 0, len(req.devices)
            )

            return OperationResult(
                success=True,
                message=f"Array {req.name} criado com sucesso (RAID {level})",
                details={
                    "name": req.name,
                    "path": md_path,
                    "level": level,
                    "devices": req.devices,
                    "spares": req.spare_devices,
                    "fault_tolerance": tolerance,
                    "formula": formula,
                },
            )
        except FileNotFoundError:
            return OperationResult(
                success=False,
                message="mdadm nao encontrado. Instale o pacote mdadm.",
                error="FileNotFoundError",
            )
        except Exception as exc:
            logger.exception("Unexpected error creating RAID array")
            return OperationResult(success=False, message=str(exc), error=repr(exc))

    # ------------------------------------------------------------------
    # Remove / Stop
    # ------------------------------------------------------------------

    def remove_array(self, name: str) -> OperationResult:
        """Safely stop and remove a RAID array."""
        array = self.get_array(name)
        if array is None:
            return OperationResult(success=False, message=f"Array {name} nao encontrado")

        md_path = array.path
        member_devices = [m.device for m in array.members]

        if array.mount_point:
            umount_result = _run(["umount", array.mount_point], check=False)
            if umount_result.returncode != 0:
                return OperationResult(
                    success=False,
                    message=f"Falha ao desmontar {array.mount_point}",
                    error=umount_result.stderr,
                )

        stop_result = _run([self.mdadm_bin, "--stop", md_path], check=False)
        if stop_result.returncode != 0:
            return OperationResult(
                success=False,
                message=f"Falha ao parar o array {name}",
                error=stop_result.stderr,
            )

        for dev in member_devices:
            zr = _run([self.mdadm_bin, "--zero-superblock", dev], check=False)
            if zr.returncode != 0:
                logger.warning("Could not zero superblock on %s: %s", dev, zr.stderr)

        self._save_mdadm_conf()

        return OperationResult(
            success=True,
            message=f"Array {name} removido com sucesso",
            details={"name": name, "freed_devices": member_devices},
        )

    # ------------------------------------------------------------------
    # Hot Spare
    # ------------------------------------------------------------------

    def add_hot_spare(self, req: RaidAddSpareRequest) -> OperationResult:
        """Add a hot spare device to an existing array."""
        md_path = f"/dev/{req.array_name}"
        cmd = [self.mdadm_bin, md_path, "--add", req.device]

        try:
            result = _run(cmd, check=False)
            if result.returncode != 0:
                return OperationResult(
                    success=False,
                    message=f"Falha ao adicionar spare {req.device} em {req.array_name}",
                    error=result.stderr,
                )
            self._save_mdadm_conf()
            return OperationResult(
                success=True,
                message=f"Dispositivo {req.device} adicionado como spare em {req.array_name}",
                details={"array": req.array_name, "device": req.device},
            )
        except Exception as exc:
            return OperationResult(success=False, message=str(exc), error=repr(exc))

    def remove_faulty_device(self, array_name: str, device: str) -> OperationResult:
        """Mark a device as faulty and remove it from the array."""
        md_path = f"/dev/{array_name}"

        fail_result = _run([self.mdadm_bin, md_path, "--fail", device], check=False)
        if fail_result.returncode != 0:
            return OperationResult(
                success=False,
                message=f"Falha ao marcar {device} como defeituoso",
                error=fail_result.stderr,
            )

        rem_result = _run([self.mdadm_bin, md_path, "--remove", device], check=False)
        if rem_result.returncode != 0:
            return OperationResult(
                success=False,
                message=f"Falha ao remover {device} do array",
                error=rem_result.stderr,
            )

        return OperationResult(
            success=True,
            message=f"Dispositivo {device} removido de {array_name}",
            details={"array": array_name, "removed": device},
        )

    # ------------------------------------------------------------------
    # Health Monitoring
    # ------------------------------------------------------------------

    def health_check(self) -> Dict:
        """Return a health summary of all arrays."""
        arrays = self.list_arrays()
        summary: Dict = {
            "healthy": 0,
            "degraded": 0,
            "failed": 0,
            "resyncing": 0,
            "arrays": [],
        }
        for arr in arrays:
            status = {
                "name": arr.name,
                "level": arr.level.value,
                "state": arr.state.value,
                "active_devices": arr.active_devices,
                "failed_devices": arr.failed_devices,
                "spare_devices": arr.spare_devices,
                "resync": arr.resync.dict() if arr.resync else None,
            }
            summary["arrays"].append(status)

            if arr.state == RaidState.ACTIVE:
                summary["healthy"] += 1
            elif arr.state == RaidState.DEGRADED:
                summary["degraded"] += 1
            elif arr.state == RaidState.FAILED:
                summary["failed"] += 1
            elif arr.state == RaidState.RESYNCING:
                summary["resyncing"] += 1

        return summary

    def is_degraded(self, name: str) -> bool:
        """Return True if the array is in a degraded state."""
        array = self.get_array(name)
        if array is None:
            return False
        return array.state in (RaidState.DEGRADED, RaidState.RECOVERING)

    def wait_for_resync(self, name: str, poll_seconds: int = 10, timeout: int = 3600) -> bool:
        """Block until array resync completes or timeout."""
        start = time.time()
        while time.time() - start < timeout:
            progress = self.get_resync_progress(name)
            if progress is None:
                return True
            logger.info(
                "Resync %s: %.1f%% (%s KB/s)", name, progress.progress_pct, progress.speed_kbps
            )
            time.sleep(poll_seconds)
        return False

    # ------------------------------------------------------------------
    # mdadm.conf
    # ------------------------------------------------------------------

    def _save_mdadm_conf(self, path: str = "/etc/mdadm/mdadm.conf") -> None:
        """Update /etc/mdadm/mdadm.conf to reflect current arrays."""
        try:
            result = _run(
                [self.mdadm_bin, "--detail", "--scan", "--verbose"], check=False
            )
            if result.returncode == 0:
                conf_path = Path(path)
                conf_path.parent.mkdir(parents=True, exist_ok=True)
                existing = conf_path.read_text() if conf_path.exists() else ""
                non_array_lines = [
                    ln for ln in existing.splitlines() if not ln.startswith("ARRAY")
                ]
                new_content = "\n".join(non_array_lines) + "\n" + result.stdout
                conf_path.write_text(new_content)
        except Exception as exc:
            logger.warning("Could not update mdadm.conf: %s", exc)

    # ------------------------------------------------------------------
    # Capacity Utility
    # ------------------------------------------------------------------

    @staticmethod
    def capacity_info(
        level: RaidLevel, disk_size_bytes: int, num_disks: int
    ) -> Dict:
        usable, tolerance, formula = calculate_capacity(level, disk_size_bytes, num_disks)
        return {
            "level": level.value,
            "num_disks": num_disks,
            "disk_size_bytes": disk_size_bytes,
            "usable_bytes": usable,
            "fault_tolerance": tolerance,
            "formula": formula,
            "efficiency_pct": round(usable / (num_disks * disk_size_bytes) * 100, 1)
            if disk_size_bytes > 0
            else 0,
        }


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

raid_service = RaidService()
