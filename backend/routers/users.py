"""
NayBinho NAS — Users and Auth Router.

Endpoints:
  POST /api/auth/login     — Authenticate and retrieve JWT token
  POST /api/auth/logout    — Invalidate session / client-side clear
  GET  /api/users          — List all users (admin only)
  POST /api/users          — Create user (admin only)
  DELETE /api/users/{username} — Delete user (admin only)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt
from pydantic import BaseModel

from config import settings
from middleware.auth import decode_token
from services import user_service

router = APIRouter(tags=["Users & Auth"])
security = HTTPBearer()

def _require_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    payload = decode_token(credentials.credentials)
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return payload

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    role: str
    username: str

class UserCreate(BaseModel):
    username: str
    password: str
    role: str = "user"
    email: Optional[str] = ""
    full_name: Optional[str] = ""

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt

@router.post("/auth/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    user = user_service.get_user(req.username)
    if not user or not user_service.verify_password(req.password, user.get("hashed_password", "")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.get("disabled", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled")

    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    token = create_access_token(
        data={"sub": user["username"], "role": user.get("role", "user")},
        expires_delta=access_token_expires,
    )
    return TokenResponse(
        access_token=token,
        expires_in=int(access_token_expires.total_seconds()),
        role=user.get("role", "user"),
        username=user["username"],
    )

@router.post("/auth/logout")
async def logout():
    return {"message": "Logged out successfully"}

@router.get("/users")
async def list_users(_: dict = Depends(_require_admin)):
    return user_service.list_users()

@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, _: dict = Depends(_require_admin)):
    try:
        new_user = user_service.create_user(user.model_dump())
        return new_user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.delete("/users/{username}")
async def delete_user(username: str, admin: dict = Depends(_require_admin)):
    if username == admin.get("sub"):
        raise HTTPException(status_code=400, detail="Cannot delete current logged-in admin")
    deleted = user_service.delete_user(username)
    if not deleted:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": f"User {username} deleted"}
