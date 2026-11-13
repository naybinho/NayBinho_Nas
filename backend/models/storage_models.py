"""
NayBinho NAS — Storage Pydantic Models
Defines all data models for disks, SMART, RAID, volumes, and shares.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class DiskType(str, Enum):
    HDD = "hdd"
    SSD = "ssd"
    NVME = "nvme"
    USB = "usb"
    UNKNOWN = "unknown"


class SmartHealth(str, Enum):
    GOOD = "good"
    WARNING = "warning"
    CRITICAL = "critical"
    FAILED = "failed"
    UNKNOWN = "unknown"


class RaidLevel(int, Enum):
    RAID0 = 0
    RAID1 = 1
    RAID5 = 5
    RAID6 = 6
    RAID10 = 10


class RaidState(str, Enum):
    ACTIVE = "active"
    DEGRADED = "degraded"
    RESYNCING = "resyncing"
    RECOVERING = "recovering"
    FAILED = "failed"
    INACTIVE = "inactive"
    UNKNOWN = "unknown"


class FilesystemType(str, Enum):
    EXT4 = "ext4"
    XFS = "xfs"
    BTRFS = "btrfs"
    ZFS = "zfs"
    NTFS = "ntfs"
    VFAT = "vfat"
    SWAP = "swap"
    NONE = "none"


class ShareProtocol(str, Enum):
    SMB = "smb"
    NFS = "nfs"


class ShareState(str, Enum):
    ACTIVE = "active"
    STOPPED = "stopped"
    ERROR = "error"


class SmartTestType(str, Enum):
    SHORT = "short"
    LONG = "long"
    CONVEYANCE = "conveyance"


class SmartTestStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"
    NOT_RUN = "not_run"
    ABORTED = "aborted"


class ZfsPoolState(str, Enum):
    ONLINE = "ONLINE"
    DEGRADED = "DEGRADED"
    FAULTED = "FAULTED"
    OFFLINE = "OFFLINE"
    REMOVED = "REMOVED"
    UNAVAIL = "UNAVAIL"


# ---------------------------------------------------------------------------
# Disk Models
# ---------------------------------------------------------------------------

class DiskPartition(BaseModel):
    name: str                           # e.g. "sda1"
    path: str                           # e.g. "/dev/sda1"
    size_bytes: int
    filesystem: Optional[FilesystemType] = None
    mount_point: Optional[str] = None
    label: Optional[str] = None
    uuid: Optional[str] = None
    used_bytes: Optional[int] = None
    available_bytes: Optional[int] = None


class DiskInfo(BaseModel):
    name: str                           # e.g. "sda"
    path: str                           # e.g. "/dev/sda"
    model: Optional[str] = None
    serial: Optional[str] = None
    firmware: Optional[str] = None
    vendor: Optional[str] = None
    disk_type: DiskType = DiskType.UNKNOWN
    size_bytes: int = 0
    rpm: Optional[int] = None           # 0 for SSD/NVMe
    temperature_celsius: Optional[float] = None
    smart_health: SmartHealth = SmartHealth.UNKNOWN
    partitions: List[DiskPartition] = Field(default_factory=list)
    in_raid: bool = False
    raid_array: Optional[str] = None    # md device name if member of RAID
    is_hot_spare: bool = False
    rotational: bool = True
    transport: Optional[str] = None     # SATA, SAS, NVMe, USB
    wwn: Optional[str] = None


# ---------------------------------------------------------------------------
# SMART Models
# ---------------------------------------------------------------------------

class SmartAttribute(BaseModel):
    id: int
    name: str
    flag: Optional[str] = None
    value: int                          # Normalized value (0-253)
    worst: int
    threshold: int
    raw_value: int
    raw_string: Optional[str] = None
    when_failed: Optional[str] = None
    is_critical: bool = False


class SmartTest(BaseModel):
    test_type: SmartTestType
    status: SmartTestStatus
    lifetime_hours: Optional[int] = None
    lba_of_first_error: Optional[str] = None
    timestamp: Optional[datetime] = None


class SmartReport(BaseModel):
    device: str                         # e.g. "/dev/sda"
    model: Optional[str] = None
    serial: Optional[str] = None
    firmware: Optional[str] = None
    capacity_bytes: Optional[int] = None
    smart_enabled: bool = False
    overall_health: SmartHealth = SmartHealth.UNKNOWN
    overall_assessment: str = ""        # human-readable summary

    # Critical counters
    reallocated_sectors: int = 0
    pending_sectors: int = 0
    uncorrectable_errors: int = 0
    temperature_celsius: Optional[float] = None
    power_on_hours: Optional[int] = None
    power_cycle_count: Optional[int] = None
    start_stop_count: Optional[int] = None

    attributes: List[SmartAttribute] = Field(default_factory=list)
    tests: List[SmartTest] = Field(default_factory=list)
    raw_output: Optional[str] = None
    collected_at: datetime = Field(default_factory=datetime.utcnow)


class SmartHistory(BaseModel):
    device: str
    readings: List[SmartReport] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# RAID Models
# ---------------------------------------------------------------------------

class RaidMember(BaseModel):
    device: str                         # e.g. "/dev/sdb"
    role: str                           # e.g. "active sync", "spare", "faulty"
    state: str
    slot: Optional[int] = None          # position in array (0-based)
    is_faulty: bool = False
    is_spare: bool = False


class RaidResyncInfo(BaseModel):
    action: str                         # "resync", "recovery", "check", "repair"
    progress_pct: float = 0.0
    speed_kbps: Optional[int] = None
    estimated_finish: Optional[str] = None
    blocks_done: Optional[int] = None
    blocks_total: Optional[int] = None


class RaidArray(BaseModel):
    name: str                           # e.g. "md0"
    path: str                           # e.g. "/dev/md0"
    level: RaidLevel
    state: RaidState = RaidState.UNKNOWN
    size_bytes: int = 0
    usable_bytes: int = 0
    chunk_size_kb: int = 512
    members: List[RaidMember] = Field(default_factory=list)
    total_devices: int = 0
    active_devices: int = 0
    failed_devices: int = 0
    spare_devices: int = 0
    uuid: Optional[str] = None
    created_at: Optional[datetime] = None
    resync: Optional[RaidResyncInfo] = None
    filesystem: Optional[FilesystemType] = None
    mount_point: Optional[str] = None
    metadata_version: Optional[str] = None

    # Derived / informational
    fault_tolerance: int = 0            # Number of disks that can fail
    description: str = ""


class RaidCreateRequest(BaseModel):
    name: str = Field(..., description="Array name, e.g. 'md0'")
    level: RaidLevel
    devices: List[str] = Field(..., min_length=2, description="List of block device paths")
    spare_devices: List[str] = Field(default_factory=list)
    chunk_size_kb: int = 512
    metadata_version: str = "1.2"


class RaidAddSpareRequest(BaseModel):
    array_name: str
    device: str


# ---------------------------------------------------------------------------
# Volume / Filesystem Models
# ---------------------------------------------------------------------------

class MountOptions(BaseModel):
    rw: bool = True
    noatime: bool = True
    nodiratime: bool = False
    noexec: bool = False
    nosuid: bool = False
    sync: bool = False
    extra: List[str] = Field(default_factory=list)


class Volume(BaseModel):
    name: str
    device: str                         # block device or ZFS dataset path
    filesystem: FilesystemType
    size_bytes: int = 0
    used_bytes: int = 0
    available_bytes: int = 0
    usage_pct: float = 0.0
    mount_point: Optional[str] = None
    is_mounted: bool = False
    uuid: Optional[str] = None
    label: Optional[str] = None
    mount_options: Optional[MountOptions] = None
    in_fstab: bool = False
    is_raid: bool = False


class FormatRequest(BaseModel):
    device: str
    filesystem: FilesystemType
    label: Optional[str] = None
    force: bool = False


class MountRequest(BaseModel):
    device: str
    mount_point: str
    filesystem: Optional[FilesystemType] = None
    options: Optional[MountOptions] = None
    persist: bool = True                # Add to /etc/fstab


class FstabEntry(BaseModel):
    device: str                         # UUID=... or /dev/...
    mount_point: str
    filesystem: str
    options: str = "defaults"
    dump: int = 0
    pass_num: int = 0


# ---------------------------------------------------------------------------
# ZFS Models
# ---------------------------------------------------------------------------

class ZfsDataset(BaseModel):
    name: str                           # pool/dataset
    kind: str = "filesystem"            # filesystem | snapshot | volume
    size_bytes: Optional[int] = None
    used_bytes: Optional[int] = None
    available_bytes: Optional[int] = None
    referenced_bytes: Optional[int] = None
    mount_point: Optional[str] = None
    compression: Optional[str] = None
    quota_bytes: Optional[int] = None
    reservation_bytes: Optional[int] = None
    created_at: Optional[datetime] = None


class ZfsPool(BaseModel):
    name: str
    state: ZfsPoolState = ZfsPoolState.ONLINE
    status: Optional[str] = None
    size_bytes: int = 0
    allocated_bytes: int = 0
    free_bytes: int = 0
    health: str = "ONLINE"
    scan_status: Optional[str] = None
    vdevs: List[Dict] = Field(default_factory=list)
    datasets: List[ZfsDataset] = Field(default_factory=list)


class ZfsPoolCreateRequest(BaseModel):
    name: str
    vdev_type: str = "mirror"           # stripe | mirror | raidz | raidz2 | raidz3
    devices: List[str]
    mount_point: Optional[str] = None
    options: Dict[str, str] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Disk Quota Models
# ---------------------------------------------------------------------------

class DiskQuota(BaseModel):
    path: str
    user_or_group: str
    is_group: bool = False
    soft_limit_bytes: Optional[int] = None
    hard_limit_bytes: Optional[int] = None
    used_bytes: int = 0
    grace_period: Optional[str] = None


# ---------------------------------------------------------------------------
# Share / Export Models
# ---------------------------------------------------------------------------

class SmbShare(BaseModel):
    name: str                           # Share name visible on network
    path: str                           # Filesystem path
    comment: Optional[str] = None
    browseable: bool = True
    writable: bool = True
    guest_ok: bool = False
    valid_users: List[str] = Field(default_factory=list)
    read_only_users: List[str] = Field(default_factory=list)
    admin_users: List[str] = Field(default_factory=list)
    create_mask: str = "0664"
    directory_mask: str = "0775"
    force_user: Optional[str] = None
    force_group: Optional[str] = None
    recycle_bin: bool = False
    extra_options: Dict[str, str] = Field(default_factory=dict)


class NfsExport(BaseModel):
    path: str
    clients: List[str] = Field(default_factory=list)   # e.g. ["192.168.1.0/24", "*"]
    options: str = "rw,sync,no_subtree_check"
    all_squash: bool = False
    no_root_squash: bool = False
    anonuid: Optional[int] = None
    anongid: Optional[int] = None


class Share(BaseModel):
    id: str                             # Unique identifier (name or path hash)
    protocol: ShareProtocol
    name: str                           # Human-readable name
    path: str
    state: ShareState = ShareState.ACTIVE
    smb_config: Optional[SmbShare] = None
    nfs_config: Optional[NfsExport] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class SambaUser(BaseModel):
    username: str
    full_name: Optional[str] = None
    enabled: bool = True


class ShareServiceStatus(BaseModel):
    smb_running: bool = False
    nfs_running: bool = False
    smb_pid: Optional[int] = None
    nfs_pid: Optional[int] = None
    smb_version: Optional[str] = None
    nfs_version: Optional[str] = None


# ---------------------------------------------------------------------------
# API Response Wrappers
# ---------------------------------------------------------------------------

class StorageSummary(BaseModel):
    total_disks: int = 0
    total_capacity_bytes: int = 0
    total_used_bytes: int = 0
    total_raid_arrays: int = 0
    degraded_arrays: int = 0
    disks_with_warnings: int = 0
    disks_with_errors: int = 0
    total_shares: int = 0
    volumes: List[Volume] = Field(default_factory=list)
    disks: List[DiskInfo] = Field(default_factory=list)
    raid_arrays: List[RaidArray] = Field(default_factory=list)
    shares: List[Share] = Field(default_factory=list)


class OperationResult(BaseModel):
    success: bool
    message: str
    details: Optional[Dict] = None
    error: Optional[str] = None
