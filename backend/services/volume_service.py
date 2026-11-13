"""
NayBinho NAS — Volume and Storage Management Service
Manages physical disks, partition discovery, formatting (ext4, xfs, btrfs),
mounts and /etc/fstab persistence, ZFS pool/dataset workflows, and directory/disk quotas.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional

from backend.models.storage_models import (
    DiskInfo,
    DiskPartition,
    DiskQuota,
    DiskType,
    FilesystemType,
    FormatRequest,
    FstabEntry,
    MountOptions,
    MountRequest,
    OperationResult,
    SmartHealth,
    Volume,
    ZfsDataset,
    ZfsPool,
    ZfsPoolCreateRequest,
    ZfsPoolState,
)

logger = logging.getLogger(__name__)

FSTAB_PATH = "/etc/fstab"


def _run_cmd(cmd: List[str], check: bool = False) -> subprocess.CompletedProcess:
    logger.debug("Executing storage command: %s", " ".join(cmd))
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


class VolumeService:
    """Manages disks, formatting, filesystem mounts, ZFS pools and storage quotas."""

    def __init__(self, fstab_path: str = FSTAB_PATH):
        self.fstab_path = Path(fstab_path)

    # -----------------------------------------------------------------------
    # Disk Discovery (lsblk & /proc/partitions)
    # -----------------------------------------------------------------------

    def list_disks(self) -> List[DiskInfo]:
        """
        Lists all block devices using lsblk JSON output enriched with disk details.
        """
        cmd = [
            "lsblk",
            "-J",
            "-b",
            "-o",
            "NAME,PATH,SIZE,ROTA,TYPE,MOUNTPOINT,FSTYPE,LABEL,UUID,MODEL,SERIAL,REV,TRAN,WWN",
        ]
        res = _run_cmd(cmd)
        if res.returncode != 0 or not res.stdout:
            return self._fallback_list_partitions()

        disks: List[DiskInfo] = []
        try:
            tree = json.loads(res.stdout)
            blockdevices = tree.get("blockdevices", [])
            for item in blockdevices:
                # We are interested in disk and loop or nvme root devices
                dev_type_str = item.get("type", "").lower()
                name = item.get("name", "")
                if dev_type_str not in ("disk", "loop") and not name.startswith("nvme"):
                    continue

                # Skip small loops
                if dev_type_str == "loop" and int(item.get("size") or 0) < 1024 * 1024 * 100:
                    continue

                rotational = bool(item.get("rota", 1))
                tran = (item.get("tran") or "").lower()
                d_type = DiskType.HDD
                if "nvme" in tran or name.startswith("nvme"):
                    d_type = DiskType.NVME
                elif not rotational:
                    d_type = DiskType.SSD
                elif "usb" in tran:
                    d_type = DiskType.USB

                partitions: List[DiskPartition] = []
                for child in item.get("children", []):
                    c_fs = None
                    if child.get("fstype"):
                        try:
                            c_fs = FilesystemType(child.get("fstype").lower())
                        except ValueError:
                            c_fs = FilesystemType.NONE

                    part = DiskPartition(
                        name=child.get("name", ""),
                        path=child.get("path") or f"/dev/{child.get('name')}",
                        size_bytes=int(child.get("size") or 0),
                        filesystem=c_fs,
                        mount_point=child.get("mountpoint"),
                        label=child.get("label"),
                        uuid=child.get("uuid"),
                    )
                    partitions.append(part)

                # Check if entire device is mounted or part of RAID
                d_info = DiskInfo(
                    name=name,
                    path=item.get("path") or f"/dev/{name}",
                    model=item.get("model", "").strip() if item.get("model") else None,
                    serial=item.get("serial", "").strip() if item.get("serial") else None,
                    firmware=item.get("rev", "").strip() if item.get("rev") else None,
                    disk_type=d_type,
                    size_bytes=int(item.get("size") or 0),
                    rotational=rotational,
                    transport=tran,
                    wwn=item.get("wwn"),
                    partitions=partitions,
                    smart_health=SmartHealth.UNKNOWN,
                )
                disks.append(d_info)

        except Exception as e:
            logger.error("Error parsing lsblk output: %s", e)
            return self._fallback_list_partitions()

        return disks

    def _fallback_list_partitions(self) -> List[DiskInfo]:
        """Fallback disk reader using /proc/partitions."""
        disks: List[DiskInfo] = []
        partitions_file = Path("/proc/partitions")
        if not partitions_file.exists():
            return disks

        lines = partitions_file.read_text().splitlines()
        for line in lines[2:]:
            parts = line.split()
            if len(parts) >= 4:
                major, minor, blocks, name = parts[0], parts[1], parts[2], parts[3]
                if re.match(r"^(sd[a-z]|vd[a-z]|nvme\d+n\d+)$", name):
                    disks.append(
                        DiskInfo(
                            name=name,
                            path=f"/dev/{name}",
                            size_bytes=int(blocks) * 1024,
                            disk_type=DiskType.HDD,
                        )
                    )
        return disks

    # -----------------------------------------------------------------------
    # Formatting (ext4, xfs, btrfs)
    # -----------------------------------------------------------------------

    def format_volume(self, req: FormatRequest) -> OperationResult:
        """
        Formats a disk or partition with the chosen filesystem.
        """
        device = req.device
        fs = req.filesystem

        # Validate filesystem
        if fs == FilesystemType.EXT4:
            cmd = ["mkfs.ext4", "-F"]
            if req.label:
                cmd += ["-L", req.label]
            cmd.append(device)
        elif fs == FilesystemType.XFS:
            cmd = ["mkfs.xfs", "-f"]
            if req.label:
                cmd += ["-L", req.label]
            cmd.append(device)
        elif fs == FilesystemType.BTRFS:
            cmd = ["mkfs.btrfs", "-f"]
            if req.label:
                cmd += ["-L", req.label]
            cmd.append(device)
        else:
            return OperationResult(
                success=False,
                message=f"Sistema de arquivos '{fs.value}' não suportado para formatação direta.",
            )

        res = _run_cmd(cmd)
        if res.returncode != 0:
            return OperationResult(
                success=False,
                message=f"Erro ao formatar {device} com {fs.value}",
                error=res.stderr or res.stdout,
            )

        return OperationResult(
            success=True,
            message=f"Dispositivo {device} formatado com sucesso em {fs.value.upper()}.",
            details={"device": device, "filesystem": fs.value, "label": req.label},
        )

    # -----------------------------------------------------------------------
    # Volume Discovery & Mounts
    # -----------------------------------------------------------------------

    def list_volumes(self) -> List[Volume]:
        """Lists active mounts and volumes."""
        volumes: List[Volume] = []
        cmd = ["findmnt", "-J", "-b", "-o", "TARGET,SOURCE,FSTYPE,OPTIONS,SIZE,USED,AVAIL,USE%"]
        res = _run_cmd(cmd)

        if res.returncode == 0 and res.stdout:
            try:
                data = json.loads(res.stdout)
                fs_list = data.get("filesystems", [])
                for item in fs_list:
                    target = item.get("target", "")
                    src = item.get("source", "")
                    fstype = item.get("fstype", "")

                    # Filter out kernel virtual filesystems
                    if fstype in ("tmpfs", "devtmpfs", "sysfs", "proc", "cgroup", "cgroup2", "squashfs", "overlay"):
                        continue
                    if target.startswith(("/sys", "/proc", "/dev", "/run")):
                        continue

                    size = int(item.get("size") or 0)
                    used = int(item.get("used") or 0)
                    avail = int(item.get("avail") or 0)
                    use_pct_str = (item.get("use%") or "0%").rstrip("%")
                    use_pct = float(use_pct_str) if use_pct_str.replace(".", "").isdigit() else 0.0

                    try:
                        fs_enum = FilesystemType(fstype.lower())
                    except ValueError:
                        fs_enum = FilesystemType.NONE

                    vol = Volume(
                        name=Path(target).name or "root",
                        device=src,
                        filesystem=fs_enum,
                        size_bytes=size,
                        used_bytes=used,
                        available_bytes=avail,
                        usage_pct=use_pct,
                        mount_point=target,
                        is_mounted=True,
                        is_raid=("md" in src),
                    )
                    volumes.append(vol)
            except Exception as e:
                logger.error("Error parsing findmnt: %s", e)

        return volumes

    def mount_volume(self, req: MountRequest) -> OperationResult:
        """Mounts a device to a target directory and optionally persists to /etc/fstab."""
        target_dir = Path(req.mount_point)
        target_dir.mkdir(parents=True, exist_ok=True)

        cmd = ["mount"]
        if req.filesystem and req.filesystem != FilesystemType.NONE:
            cmd += ["-t", req.filesystem.value]

        opts = []
        if req.options:
            if req.options.rw:
                opts.append("rw")
            if req.options.noatime:
                opts.append("noatime")
            if req.options.extra:
                opts.extend(req.options.extra)

        if opts:
            cmd += ["-o", ",".join(opts)]

        cmd += [req.device, req.mount_point]
        res = _run_cmd(cmd)

        if res.returncode != 0:
            return OperationResult(
                success=False,
                message=f"Falha ao montar {req.device} em {req.mount_point}",
                error=res.stderr or res.stdout,
            )

        if req.persist:
            fs_type = req.filesystem.value if req.filesystem else "auto"
            opt_str = ",".join(opts) if opts else "defaults"
            self.add_fstab_entry(
                FstabEntry(
                    device=req.device,
                    mount_point=req.mount_point,
                    filesystem=fs_type,
                    options=opt_str,
                )
            )

        return OperationResult(
            success=True,
            message=f"Volume {req.device} montado com sucesso em {req.mount_point}.",
            details={"device": req.device, "mount_point": req.mount_point},
        )

    def unmount_volume(self, mount_point_or_device: str, remove_fstab: bool = False) -> OperationResult:
        """Unmounts a volume."""
        cmd = ["umount", mount_point_or_device]
        res = _run_cmd(cmd)
        if res.returncode != 0:
            return OperationResult(
                success=False,
                message=f"Falha ao desmontar {mount_point_or_device}",
                error=res.stderr or res.stdout,
            )

        if remove_fstab:
            self.remove_fstab_entry(mount_point_or_device)

        return OperationResult(
            success=True,
            message=f"{mount_point_or_device} desmontado com sucesso.",
            details={"target": mount_point_or_device},
        )

    # -----------------------------------------------------------------------
    # /etc/fstab Management
    # -----------------------------------------------------------------------

    def get_fstab_entries(self) -> List[FstabEntry]:
        entries: List[FstabEntry] = []
        if not self.fstab_path.exists():
            return entries

        lines = self.fstab_path.read_text().splitlines()
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 4:
                entries.append(
                    FstabEntry(
                        device=parts[0],
                        mount_point=parts[1],
                        filesystem=parts[2],
                        options=parts[3],
                        dump=int(parts[4]) if len(parts) > 4 else 0,
                        pass_num=int(parts[5]) if len(parts) > 5 else 0,
                    )
                )
        return entries

    def add_fstab_entry(self, entry: FstabEntry) -> None:
        """Appends or updates an entry in /etc/fstab."""
        try:
            entries = self.get_fstab_entries()
            # Remove any existing match by device or mount point
            filtered = [e for e in entries if e.device != entry.device and e.mount_point != entry.mount_point]
            filtered.append(entry)

            content_lines = ["# /etc/fstab: static file system information generated by NayBinho NAS"]
            for e in filtered:
                content_lines.append(f"{e.device:<40} {e.mount_point:<25} {e.filesystem:<10} {e.options:<20} {e.dump} {e.pass_num}")

            self.fstab_path.write_text("\n".join(content_lines) + "\n")
        except Exception as e:
            logger.warning("Failed writing to fstab: %s", e)

    def remove_fstab_entry(self, target: str) -> None:
        """Removes an entry matching device or mount point from /etc/fstab."""
        try:
            entries = self.get_fstab_entries()
            filtered = [e for e in entries if e.device != target and e.mount_point != target]
            content_lines = ["# /etc/fstab: static file system information generated by NayBinho NAS"]
            for e in filtered:
                content_lines.append(f"{e.device:<40} {e.mount_point:<25} {e.filesystem:<10} {e.options:<20} {e.dump} {e.pass_num}")
            self.fstab_path.write_text("\n".join(content_lines) + "\n")
        except Exception as e:
            logger.warning("Failed updating fstab: %s", e)

    # -----------------------------------------------------------------------
    # ZFS Pool & Dataset Management
    # -----------------------------------------------------------------------

    def list_zfs_pools(self) -> List[ZfsPool]:
        """Lists ZFS storage pools via zpool list and status."""
        pools: List[ZfsPool] = []
        cmd = ["zpool", "list", "-H", "-p", "-o", "name,size,alloc,free,health"]
        res = _run_cmd(cmd)
        if res.returncode != 0:
            return pools

        for line in res.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 5:
                name, size, alloc, free, health = parts[0], parts[1], parts[2], parts[3], parts[4]
                state_enum = ZfsPoolState.ONLINE
                try:
                    state_enum = ZfsPoolState(health.upper())
                except ValueError:
                    pass

                pool = ZfsPool(
                    name=name,
                    size_bytes=int(size) if size.isdigit() else 0,
                    allocated_bytes=int(alloc) if alloc.isdigit() else 0,
                    free_bytes=int(free) if free.isdigit() else 0,
                    health=health,
                    state=state_enum,
                    datasets=self.list_zfs_datasets(name),
                )
                pools.append(pool)
        return pools

    def list_zfs_datasets(self, pool_name: Optional[str] = None) -> List[ZfsDataset]:
        """Lists datasets within pools."""
        datasets: List[ZfsDataset] = []
        cmd = ["zfs", "list", "-H", "-p", "-o", "name,type,used,avail,refer,mountpoint"]
        if pool_name:
            cmd.append(pool_name)
        res = _run_cmd(cmd)
        if res.returncode != 0:
            return datasets

        for line in res.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 6:
                d_name, d_type, used, avail, refer, mp = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
                datasets.append(
                    ZfsDataset(
                        name=d_name,
                        kind=d_type,
                        used_bytes=int(used) if used.isdigit() else 0,
                        available_bytes=int(avail) if avail.isdigit() else 0,
                        referenced_bytes=int(refer) if refer.isdigit() else 0,
                        mount_point=mp if mp != "none" else None,
                    )
                )
        return datasets

    def create_zfs_pool(self, req: ZfsPoolCreateRequest) -> OperationResult:
        """Creates a ZFS storage pool."""
        cmd = ["zpool", "create", "-f"]
        if req.mount_point:
            cmd += ["-m", req.mount_point]

        for k, v in req.options.items():
            cmd += ["-O", f"{k}={v}"]

        cmd.append(req.name)
        if req.vdev_type and req.vdev_type != "stripe":
            cmd.append(req.vdev_type)
        cmd.extend(req.devices)

        res = _run_cmd(cmd)
        if res.returncode != 0:
            return OperationResult(
                success=False,
                message=f"Falha ao criar ZFS pool '{req.name}'",
                error=res.stderr or res.stdout,
            )

        return OperationResult(
            success=True,
            message=f"ZFS Pool '{req.name}' criado com sucesso.",
            details={"pool": req.name, "vdev_type": req.vdev_type, "devices": req.devices},
        )

    def destroy_zfs_pool(self, pool_name: str) -> OperationResult:
        """Destroys a ZFS pool."""
        cmd = ["zpool", "destroy", "-f", pool_name]
        res = _run_cmd(cmd)
        if res.returncode != 0:
            return OperationResult(
                success=False,
                message=f"Falha ao destruir ZFS pool '{pool_name}'",
                error=res.stderr or res.stdout,
            )
        return OperationResult(
            success=True,
            message=f"ZFS Pool '{pool_name}' destruído com sucesso.",
            details={"pool": pool_name},
        )

    # -----------------------------------------------------------------------
    # Quota Management
    # -----------------------------------------------------------------------

    def set_zfs_quota(self, dataset: str, quota_bytes: int) -> OperationResult:
        """Sets dataset quota in ZFS."""
        cmd = ["zfs", "set", f"quota={quota_bytes}", dataset]
        res = _run_cmd(cmd)
        if res.returncode == 0:
            return OperationResult(
                success=True,
                message=f"Quota de {quota_bytes} bytes aplicada ao dataset {dataset}.",
            )
        return OperationResult(
            success=False,
            message=f"Falha ao definir quota para {dataset}.",
            error=res.stderr or res.stdout,
        )

    def get_directory_quota(self, path: str) -> Optional[DiskQuota]:
        """Checks disk usage for a path."""
        try:
            total, used, free = shutil.disk_usage(path)
            return DiskQuota(
                path=path,
                user_or_group="system",
                soft_limit_bytes=total,
                hard_limit_bytes=total,
                used_bytes=used,
            )
        except Exception as e:
            logger.warning("Could not check disk usage for %s: %s", path, e)
            return None


volume_service = VolumeService()
