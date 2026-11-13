"""
NayBinho NAS — SQLite Configuration & Database Session Manager
SQLAlchemy Engine, Session, Migrations and CRUD Helpers.
"""

import json
import logging
import os
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from backend.database.models import (
    Alert,
    AppInstallation,
    Base,
    Event,
    MetricHistory,
    RaidArray,
    Setting,
    SmartReport,
    User,
)

logger = logging.getLogger("naybinho.db")

# Default database location in production vs dev
DB_DIR = Path(os.getenv("NAYBINHO_DATA_DIR", "/opt/naybinho/data"))
try:
    DB_DIR.mkdir(parents=True, exist_ok=True)
    DB_FILE = DB_DIR / "naybinho.db"
except Exception:
    # Fallback to local execution directory if running without /opt permissions
    DB_FILE = Path("naybinho.db").resolve()

DATABASE_URL = f"sqlite:///{DB_FILE}"

# Engine with SQLite optimizations for concurrent reads
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ---------------------------------------------------------------------------
# Database Initialization & Simple Migrations
# ---------------------------------------------------------------------------
def init_db():
    """Initializes tables and applies lightweight schema migrations."""
    try:
        # Enable WAL mode for high concurrency
        with engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL;"))
            conn.execute(text("PRAGMA synchronous=NORMAL;"))
            conn.commit()

        # Create all tables defined in models
        Base.metadata.create_all(bind=engine)
        logger.info(f"Database schema initialized successfully at {DB_FILE}")

        # Seed initial default settings if empty
        _seed_default_settings()
    except Exception as exc:
        logger.error(f"Failed to initialize database: {exc}")
        raise


def _seed_default_settings():
    """Populates basic default settings."""
    defaults = {
        "cpu_percent": 90.0,
        "ram_percent": 90.0,
        "disk_percent": 85.0,
        "temperature_celsius": 70.0,
        "collect_interval_seconds": 10,
        "retention_days": 30,
        "email_enabled": False,
        "webhook_enabled": False,
        "telegram_enabled": False,
        "hostname": "naybinho-nas",
    }
    with get_db_context() as db:
        for k, v in defaults.items():
            existing = db.query(Setting).filter(Setting.key == k).first()
            if not existing:
                db.add(Setting(key=k, value=json.dumps(v), description=f"Default setting for {k}"))
        db.commit()


# ---------------------------------------------------------------------------
# Dependency for FastAPI Routers
# ---------------------------------------------------------------------------
def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for yielding database session per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """Context manager for standalone scripts or background tasks."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# CRUD Helpers
# ---------------------------------------------------------------------------

# Settings
def get_setting(key: str, default: Any = None) -> Any:
    with get_db_context() as db:
        row = db.query(Setting).filter(Setting.key == key).first()
        if not row or row.value is None:
            return default
        try:
            return json.loads(row.value)
        except Exception:
            return row.value


def set_setting(key: str, value: Any, description: Optional[str] = None):
    val_str = json.dumps(value)
    with get_db_context() as db:
        setting = db.query(Setting).filter(Setting.key == key).first()
        if setting:
            setting.value = val_str
            if description:
                setting.description = description
        else:
            setting = Setting(key=key, value=val_str, description=description)
            db.add(setting)
        db.commit()


# Alerts
def create_alert(alert_data: Dict[str, Any]) -> Alert:
    with get_db_context() as db:
        extra_str = json.dumps(alert_data.get("extra", {})) if isinstance(alert_data.get("extra"), dict) else alert_data.get("extra")
        alert = Alert(
            type=alert_data["type"],
            severity=alert_data.get("severity", "warning"),
            message=alert_data["message"],
            value=alert_data.get("value"),
            threshold=alert_data.get("threshold"),
            extra=extra_str,
            created_at=datetime.utcnow(),
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert


def get_active_alerts() -> List[Alert]:
    with get_db_context() as db:
        return db.query(Alert).filter(Alert.dismissed == False).order_by(Alert.created_at.desc()).all()


def dismiss_alert_by_id(alert_id: int, user: str = "system") -> bool:
    with get_db_context() as db:
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            alert.dismissed = True
            alert.dismissed_at = datetime.utcnow()
            alert.dismissed_by = user
            db.commit()
            return True
        return False


# Events
def record_event(actor: str, action: str, target: Optional[str] = None, result: str = "success", detail: Optional[dict] = None) -> Event:
    with get_db_context() as db:
        event = Event(
            actor=actor,
            action=action,
            target=target,
            result=result,
            detail=json.dumps(detail) if detail else None,
            timestamp=datetime.utcnow(),
        )
        db.add(event)
        db.commit()
        db.refresh(event)
        return event


# Users
def get_user_by_username(username: str) -> Optional[User]:
    with get_db_context() as db:
        return db.query(User).filter(User.username == username).first()


# App Installations
def list_installed_apps() -> List[AppInstallation]:
    with get_db_context() as db:
        return db.query(AppInstallation).all()
