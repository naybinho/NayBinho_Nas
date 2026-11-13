"""
NayBinho NAS — SQLAlchemy ORM Models
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# ---------------------------------------------------------------------------
# Metrics history — raw snapshots collected by monitor_service
# ---------------------------------------------------------------------------
class MetricHistory(Base):
    __tablename__ = "metrics_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True, default=datetime.utcnow)

    # Quick-access columns (duplicated from JSON payload for fast queries)
    cpu_pct = Column(Float, nullable=True)
    ram_pct = Column(Float, nullable=True)
    disk_pct_root = Column(Float, nullable=True)   # percent of root filesystem
    net_sent_bytes = Column(Integer, nullable=True)
    net_recv_bytes = Column(Integer, nullable=True)
    temp_max_celsius = Column(Float, nullable=True)

    # Full JSON snapshot
    payload = Column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Alerts
# ---------------------------------------------------------------------------
class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(64), nullable=False, index=True)
    severity = Column(String(16), nullable=False)  # info | warning | critical
    message = Column(Text, nullable=False)
    value = Column(Float, nullable=True)
    threshold = Column(Float, nullable=True)
    extra = Column(Text, nullable=True)  # JSON blob for device, sensor, etc.

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    dismissed = Column(Boolean, nullable=False, default=False, index=True)
    dismissed_at = Column(DateTime, nullable=True)
    dismissed_by = Column(String(64), nullable=True)


# ---------------------------------------------------------------------------
# Events — audit trail (user actions, system events)
# ---------------------------------------------------------------------------
class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    actor = Column(String(128), nullable=False)   # username or "system"
    action = Column(String(128), nullable=False)  # e.g. "app.install", "raid.create"
    target = Column(String(256), nullable=True)   # e.g. app id, device path
    result = Column(String(16), nullable=False, default="success")  # success | failure
    detail = Column(Text, nullable=True)          # JSON


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(64), nullable=False, unique=True, index=True)
    hashed_password = Column(String(256), nullable=False)
    email = Column(String(256), nullable=True)
    role = Column(String(32), nullable=False, default="user")  # admin | user | readonly
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    avatar_url = Column(String(512), nullable=True)

    # relationship
    installations = relationship("AppInstallation", back_populates="user", lazy="dynamic")


# ---------------------------------------------------------------------------
# App Installations
# ---------------------------------------------------------------------------
class AppInstallation(Base):
    __tablename__ = "app_installations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    app_id = Column(String(128), nullable=False, unique=True, index=True)
    app_name = Column(String(256), nullable=False)
    version = Column(String(64), nullable=True)
    category = Column(String(64), nullable=True)
    icon_url = Column(String(512), nullable=True)
    install_path = Column(String(512), nullable=True)
    compose_path = Column(String(512), nullable=True)
    status = Column(String(32), nullable=False, default="installed")  # installed | stopped | error | updating
    installed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)
    config = Column(Text, nullable=True)  # JSON: user-supplied env vars / ports

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    user = relationship("User", back_populates="installations")


# ---------------------------------------------------------------------------
# Settings — key-value store
# ---------------------------------------------------------------------------
class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(128), primary_key=True)
    value = Column(Text, nullable=True)
    description = Column(String(512), nullable=True)
    updated_at = Column(DateTime, nullable=True, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# RAID Arrays — persistent snapshot (supplementing live /proc/mdstat)
# ---------------------------------------------------------------------------
class RaidArray(Base):
    __tablename__ = "raid_arrays"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(64), nullable=False, unique=True, index=True)  # e.g. md0
    level = Column(String(16), nullable=False)   # 0,1,5,6,10
    devices = Column(Text, nullable=False)        # JSON list of device paths
    state = Column(String(32), nullable=False, default="clean")
    size_gb = Column(Float, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_checked = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)


# ---------------------------------------------------------------------------
# SMART Reports — per disk
# ---------------------------------------------------------------------------
class SmartReport(Base):
    __tablename__ = "smart_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device = Column(String(64), nullable=False, index=True)
    collected_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    overall_health = Column(String(16), nullable=True)  # PASSED | FAILED
    temperature = Column(Float, nullable=True)
    reallocated_sectors = Column(Integer, nullable=True)
    pending_sectors = Column(Integer, nullable=True)
    uncorrectable = Column(Integer, nullable=True)
    power_on_hours = Column(Integer, nullable=True)
    payload = Column(Text, nullable=True)  # Full JSON SMART output

    __table_args__ = (
        UniqueConstraint("device", "collected_at", name="uq_smart_device_ts"),
    )
