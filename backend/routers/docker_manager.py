"""
NayBinho NAS — Docker Manager Router.

Endpoints:
  GET  /api/docker/containers               — list all containers
  POST /api/docker/containers/start/{id}    — start container
  POST /api/docker/containers/stop/{id}     — stop container
  POST /api/docker/containers/restart/{id}  — restart container
  DELETE /api/docker/containers/{id}        — remove container
  GET  /api/docker/images                   — list images
  POST /api/docker/pull                     — pull image
  GET  /api/docker/stats/{id}               — container resource stats
  POST /api/docker/compose/deploy           — deploy docker-compose stack
  GET  /api/docker/networks                 — list networks
  POST /api/docker/networks                 — create network
  GET  /api/docker/volumes                  — list volumes
  POST /api/docker/volumes                  — create volume
  DELETE /api/docker/volumes/{name}         — remove volume
"""
from __future__ import annotations

import os
import tempfile
import subprocess
from typing import Any, Optional

import docker
from docker.errors import DockerException, NotFound, APIError
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from loguru import logger

from middleware.auth import decode_token
from config import settings

router = APIRouter(prefix="/docker", tags=["Docker"])
security = HTTPBearer()


# ── Docker client ─────────────────────────────────────────────────────────────

def _client() -> docker.DockerClient:
    try:
        return docker.from_env()
    except DockerException as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Cannot connect to Docker daemon: {exc}",
        )


# ── Auth helpers ──────────────────────────────────────────────────────────────

def _require_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    payload = decode_token(credentials.credentials)
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return payload


def _require_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return decode_token(credentials.credentials)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _container_to_dict(c) -> dict[str, Any]:
    ports = c.ports or {}
    return {
        "id": c.short_id,
        "id_full": c.id,
        "name": c.name,
        "image": c.image.tags[0] if c.image.tags else c.image.short_id,
        "status": c.status,
        "state": c.attrs.get("State", {}),
        "ports": ports,
        "created": c.attrs.get("Created", ""),
        "labels": c.labels,
        "networks": list(c.attrs.get("NetworkSettings", {}).get("Networks", {}).keys()),
        "restart_policy": c.attrs.get("HostConfig", {}).get("RestartPolicy", {}),
    }


def _image_to_dict(img) -> dict[str, Any]:
    return {
        "id": img.short_id,
        "tags": img.tags,
        "size_bytes": img.attrs.get("Size", 0),
        "created": img.attrs.get("Created", ""),
        "architecture": img.attrs.get("Architecture", ""),
        "os": img.attrs.get("Os", ""),
    }


# ── Schemas ───────────────────────────────────────────────────────────────────

class PullRequest(BaseModel):
    image: str              # e.g. "nginx:latest"
    platform: Optional[str] = None


class ComposeDeployRequest(BaseModel):
    stack_name: str
    compose_yaml: str       # raw YAML content


class NetworkCreateRequest(BaseModel):
    name: str
    driver: str = "bridge"
    internal: bool = False
    labels: Optional[dict[str, str]] = None


class VolumeCreateRequest(BaseModel):
    name: str
    driver: str = "local"
    labels: Optional[dict[str, str]] = None


# ── Container endpoints ───────────────────────────────────────────────────────

@router.get("/containers")
async def list_containers(
    all: bool = True,
    _: dict = Depends(_require_user),
):
    """List Docker containers."""
    client = _client()
    return [_container_to_dict(c) for c in client.containers.list(all=all)]


@router.post("/containers/start/{container_id}")
async def start_container(
    container_id: str,
    _: dict = Depends(_require_admin),
):
    client = _client()
    try:
        c = client.containers.get(container_id)
        c.start()
        return {"message": f"Container {container_id} started", "status": c.status}
    except NotFound:
        raise HTTPException(status_code=404, detail="Container not found")
    except APIError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/containers/stop/{container_id}")
async def stop_container(
    container_id: str,
    timeout: int = 10,
    _: dict = Depends(_require_admin),
):
    client = _client()
    try:
        c = client.containers.get(container_id)
        c.stop(timeout=timeout)
        return {"message": f"Container {container_id} stopped"}
    except NotFound:
        raise HTTPException(status_code=404, detail="Container not found")


@router.post("/containers/restart/{container_id}")
async def restart_container(
    container_id: str,
    _: dict = Depends(_require_admin),
):
    client = _client()
    try:
        c = client.containers.get(container_id)
        c.restart()
        return {"message": f"Container {container_id} restarted"}
    except NotFound:
        raise HTTPException(status_code=404, detail="Container not found")


@router.delete("/containers/{container_id}")
async def remove_container(
    container_id: str,
    force: bool = False,
    _: dict = Depends(_require_admin),
):
    client = _client()
    try:
        c = client.containers.get(container_id)
        c.remove(force=force)
        return {"message": f"Container {container_id} removed"}
    except NotFound:
        raise HTTPException(status_code=404, detail="Container not found")
    except APIError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/stats/{container_id}")
async def container_stats(container_id: str, _: dict = Depends(_require_user)):
    """Return a single stats snapshot for a container."""
    client = _client()
    try:
        c = client.containers.get(container_id)
        raw = c.stats(stream=False)
    except NotFound:
        raise HTTPException(status_code=404, detail="Container not found")

    # Calculate CPU %
    cpu_delta = (
        raw["cpu_stats"]["cpu_usage"]["total_usage"]
        - raw["precpu_stats"]["cpu_usage"]["total_usage"]
    )
    system_delta = (
        raw["cpu_stats"].get("system_cpu_usage", 0)
        - raw["precpu_stats"].get("system_cpu_usage", 0)
    )
    num_cpus = raw["cpu_stats"].get("online_cpus") or len(
        raw["cpu_stats"]["cpu_usage"].get("percpu_usage", [1])
    )
    cpu_percent = (cpu_delta / system_delta * num_cpus * 100.0) if system_delta > 0 else 0.0

    # Memory
    mem = raw.get("memory_stats", {})
    mem_usage = mem.get("usage", 0)
    mem_limit = mem.get("limit", 1)
    mem_percent = (mem_usage / mem_limit * 100.0) if mem_limit else 0.0

    # Network I/O
    net_rx, net_tx = 0, 0
    for iface_stats in raw.get("networks", {}).values():
        net_rx += iface_stats.get("rx_bytes", 0)
        net_tx += iface_stats.get("tx_bytes", 0)

    return {
        "container_id": container_id,
        "cpu_percent": round(cpu_percent, 2),
        "memory_usage_bytes": mem_usage,
        "memory_limit_bytes": mem_limit,
        "memory_percent": round(mem_percent, 2),
        "net_rx_bytes": net_rx,
        "net_tx_bytes": net_tx,
        "block_read_bytes": sum(
            b["value"] for b in raw.get("blkio_stats", {}).get("io_service_bytes_recursive", [])
            if b["op"] == "read"
        ),
        "block_write_bytes": sum(
            b["value"] for b in raw.get("blkio_stats", {}).get("io_service_bytes_recursive", [])
            if b["op"] == "write"
        ),
        "pids": raw.get("pids_stats", {}).get("current", 0),
    }


# ── Image endpoints ───────────────────────────────────────────────────────────

@router.get("/images")
async def list_images(_: dict = Depends(_require_user)):
    client = _client()
    return [_image_to_dict(img) for img in client.images.list(all=False)]


@router.post("/pull", status_code=202)
async def pull_image(
    req: PullRequest,
    background_tasks: BackgroundTasks,
    _: dict = Depends(_require_admin),
):
    """Pull a Docker image in the background."""
    def _pull():
        try:
            client = docker.from_env()
            kwargs: dict[str, Any] = {"tag": req.image}
            if req.platform:
                kwargs["platform"] = req.platform
            client.images.pull(**kwargs)
            logger.info(f"Pulled image: {req.image}")
        except Exception as exc:
            logger.error(f"Failed to pull {req.image}: {exc}")

    background_tasks.add_task(_pull)
    return {"message": f"Pulling {req.image} in background"}


# ── Compose endpoints ─────────────────────────────────────────────────────────

@router.post("/compose/deploy", status_code=202)
async def compose_deploy(
    req: ComposeDeployRequest,
    background_tasks: BackgroundTasks,
    _: dict = Depends(_require_admin),
):
    """Deploy a docker-compose stack from a YAML string."""
    stack_dir = settings.compose_projects_dir / req.stack_name
    stack_dir.mkdir(parents=True, exist_ok=True)
    compose_file = stack_dir / "docker-compose.yml"
    compose_file.write_text(req.compose_yaml)

    def _deploy():
        result = subprocess.run(
            ["docker", "compose", "-p", req.stack_name, "up", "-d", "--remove-orphans"],
            cwd=str(stack_dir),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            logger.error(f"Compose deploy failed for {req.stack_name}: {result.stderr}")
        else:
            logger.info(f"Compose stack '{req.stack_name}' deployed successfully")

    background_tasks.add_task(_deploy)
    return {"message": f"Deploying stack '{req.stack_name}' in background"}


# ── Network endpoints ─────────────────────────────────────────────────────────

@router.get("/networks")
async def list_networks(_: dict = Depends(_require_user)):
    client = _client()
    return [
        {
            "id": n.short_id,
            "name": n.name,
            "driver": n.attrs.get("Driver", ""),
            "scope": n.attrs.get("Scope", ""),
            "internal": n.attrs.get("Internal", False),
            "ipam": n.attrs.get("IPAM", {}),
            "labels": n.attrs.get("Labels", {}),
        }
        for n in client.networks.list()
    ]


@router.post("/networks", status_code=201)
async def create_network(
    req: NetworkCreateRequest,
    _: dict = Depends(_require_admin),
):
    client = _client()
    try:
        net = client.networks.create(
            name=req.name,
            driver=req.driver,
            internal=req.internal,
            labels=req.labels or {},
        )
        return {"id": net.short_id, "name": net.name}
    except APIError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Volume endpoints ──────────────────────────────────────────────────────────

@router.get("/volumes")
async def list_volumes(_: dict = Depends(_require_user)):
    client = _client()
    return [
        {
            "name": v.name,
            "driver": v.attrs.get("Driver", ""),
            "mountpoint": v.attrs.get("Mountpoint", ""),
            "created": v.attrs.get("CreatedAt", ""),
            "labels": v.attrs.get("Labels") or {},
            "scope": v.attrs.get("Scope", ""),
        }
        for v in client.volumes.list()
    ]


@router.post("/volumes", status_code=201)
async def create_volume(
    req: VolumeCreateRequest,
    _: dict = Depends(_require_admin),
):
    client = _client()
    try:
        v = client.volumes.create(
            name=req.name,
            driver=req.driver,
            labels=req.labels or {},
        )
        return {"name": v.name, "mountpoint": v.attrs.get("Mountpoint", "")}
    except APIError as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.delete("/volumes/{name}")
async def remove_volume(
    name: str,
    force: bool = False,
    _: dict = Depends(_require_admin),
):
    client = _client()
    try:
        v = client.volumes.get(name)
        v.remove(force=force)
        return {"message": f"Volume '{name}' removed"}
    except NotFound:
        raise HTTPException(status_code=404, detail="Volume not found")
    except APIError as exc:
        raise HTTPException(status_code=500, detail=str(exc))
