"""
NayBinho NAS — User Service.
Handles user storage, authentication (bcrypt), and default admin seeding.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from passlib.context import CryptContext
from loguru import logger
from config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def _load_users() -> dict[str, Any]:
    if not settings.users_db_path.exists():
        return {}
    try:
        return json.loads(settings.users_db_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.error(f"Error loading users DB: {exc}")
        return {}

def _save_users(users: dict[str, Any]):
    settings.users_db_path.parent.mkdir(parents=True, exist_ok=True)
    settings.users_db_path.write_text(json.dumps(users, indent=2), encoding="utf-8")

async def ensure_default_admin():
    users = _load_users()
    if not any(u.get("role") == "admin" for u in users.values()):
        username = settings.default_admin_username
        users[username] = {
            "username": username,
            "hashed_password": get_password_hash(settings.default_admin_password),
            "role": "admin",
            "email": "admin@naybinho.local",
            "full_name": "NayBinho Administrator",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "disabled": False,
        }
        _save_users(users)
        logger.info(f"Default admin user '{username}' created.")

def get_user(username: str) -> Optional[dict[str, Any]]:
    users = _load_users()
    return users.get(username)

def list_users() -> list[dict[str, Any]]:
    users = _load_users()
    result = []
    for u in users.values():
        clean_user = dict(u)
        clean_user.pop("hashed_password", None)
        result.append(clean_user)
    return result

def create_user(user_data: dict[str, Any]) -> dict[str, Any]:
    users = _load_users()
    username = user_data["username"]
    if username in users:
        raise ValueError(f"User '{username}' already exists")
    
    users[username] = {
        "username": username,
        "hashed_password": get_password_hash(user_data["password"]),
        "role": user_data.get("role", "user"),
        "email": user_data.get("email", ""),
        "full_name": user_data.get("full_name", ""),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "disabled": user_data.get("disabled", False),
    }
    _save_users(users)
    clean = dict(users[username])
    clean.pop("hashed_password", None)
    return clean

def delete_user(username: str) -> bool:
    users = _load_users()
    if username not in users:
        return False
    del users[username]
    _save_users(users)
    return True
