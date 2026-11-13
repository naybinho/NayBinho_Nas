"""
NayBinho NAS — Global configuration.
All settings are loaded from environment variables or .env file.
"""
from __future__ import annotations

import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────────
    app_name: str = "NayBinho NAS"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False)

    # ── API ──────────────────────────────────────────────────────────────────
    api_prefix: str = "/api"
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    workers: int = 1

    # ── Security / JWT ───────────────────────────────────────────────────────
    secret_key: str = Field(
        default="change-me-in-production-use-a-long-random-string-here-32bytes",
    )
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24 hours

    # ── Paths ────────────────────────────────────────────────────────────────
    base_dir: Path = Path(__file__).parent
    services_dir: Path = base_dir / "services"
    apps_catalog_path: Path = services_dir / "apps_catalog.json"
    appstore_sources_path: Path = services_dir / "store_sources.json"
    appstore_cache_dir: Path = base_dir / "data" / "stores_cache"
    installed_apps_path: Path = services_dir / "installed_apps.json"
    users_db_path: Path = base_dir / "data" / "users.json"
    logs_dir: Path = base_dir / "logs"

    # ── Docker ───────────────────────────────────────────────────────────────
    docker_socket: str = "unix:///var/run/docker.sock"
    compose_projects_dir: Path = Path("/opt/naybinho/compose")

    # ── Storage ──────────────────────────────────────────────────────────────
    proc_mdstat: str = "/proc/mdstat"
    shares_config_path: Path = Path("/etc/naybinho/shares.json")

    # ── CORS ─────────────────────────────────────────────────────────────────
    cors_origins: list[str] = ["*"]
    cors_allow_credentials: bool = True

    # ── Default admin ────────────────────────────────────────────────────────
    default_admin_username: str = "admin"
    default_admin_password: str = "naybinho"  # Must be changed on first login

    # ── Update & Releases ────────────────────────────────────────────────────
    github_repo: str = "naybinho/nas"
    auto_update_check_interval_hours: int = 6
    version_file: Path = Path("/opt/naybinho/VERSION")


settings = Settings()

# Ensure required directories exist at import time
for _dir in (settings.logs_dir, settings.compose_projects_dir,
             settings.users_db_path.parent):
    try:
        _dir.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass  # May fail on read-only mounts — not critical at import time
