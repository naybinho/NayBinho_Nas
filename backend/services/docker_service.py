"""
NayBinho NAS — Docker Service
Serviço completo para gerenciamento do subsistema Docker.
Suporta: containers, imagens, volumes, networks, compose, logs, stats, eventos SSE.
"""

import asyncio
import json
import logging
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional, Any

import docker
from docker.errors import APIError, DockerException, NotFound, ImageNotFound
from docker.models.containers import Container
from docker.models.images import Image
from docker.models.networks import Network
from docker.models.volumes import Volume

logger = logging.getLogger("naybinho.docker")

COMPOSE_BASE_DIR = Path("/opt/naybinho/apps")
COMPOSE_BASE_DIR.mkdir(parents=True, exist_ok=True)


class DockerService:
    """Serviço central de gerenciamento Docker para o NayBinho NAS."""

    def __init__(self):
        try:
            self.client = docker.from_env()
            self.low_level = docker.APIClient(base_url="unix://var/run/docker.sock")
            logger.info("Docker client initialized successfully.")
        except DockerException as e:
            logger.error(f"Failed to connect to Docker daemon: {e}")
            raise

    # -------------------------------------------------------------------------
    # CONTAINERS
    # -------------------------------------------------------------------------

    def list_containers(self, all: bool = True) -> List[Dict]:
        """Lista todos os containers com metadados enriquecidos."""
        containers = self.client.containers.list(all=all)
        result = []
        for c in containers:
            result.append(self._serialize_container(c))
        return result

    def get_container(self, container_id: str) -> Dict:
        """Retorna detalhes de um container específico."""
        c = self.client.containers.get(container_id)
        return self._serialize_container(c)

    def start_container(self, container_id: str) -> Dict:
        """Inicia um container parado."""
        c = self.client.containers.get(container_id)
        c.start()
        c.reload()
        logger.info(f"Container started: {container_id}")
        return self._serialize_container(c)

    def stop_container(self, container_id: str, timeout: int = 10) -> Dict:
        """Para um container em execução."""
        c = self.client.containers.get(container_id)
        c.stop(timeout=timeout)
        c.reload()
        logger.info(f"Container stopped: {container_id}")
        return self._serialize_container(c)

    def restart_container(self, container_id: str, timeout: int = 10) -> Dict:
        """Reinicia um container."""
        c = self.client.containers.get(container_id)
        c.restart(timeout=timeout)
        c.reload()
        logger.info(f"Container restarted: {container_id}")
        return self._serialize_container(c)

    def remove_container(self, container_id: str, force: bool = False, volumes: bool = False) -> bool:
        """Remove um container."""
        c = self.client.containers.get(container_id)
        c.remove(force=force, v=volumes)
        logger.info(f"Container removed: {container_id}")
        return True

    def create_container(
        self,
        image: str,
        name: Optional[str] = None,
        ports: Optional[Dict] = None,
        volumes: Optional[Dict] = None,
        environment: Optional[Dict] = None,
        restart_policy: str = "unless-stopped",
        network: Optional[str] = None,
        labels: Optional[Dict] = None,
    ) -> Dict:
        """Cria e inicia um novo container."""
        kwargs = {
            "image": image,
            "detach": True,
            "restart_policy": {"Name": restart_policy},
        }
        if name:
            kwargs["name"] = name
        if ports:
            kwargs["ports"] = ports
        if volumes:
            kwargs["volumes"] = volumes
        if environment:
            kwargs["environment"] = environment
        if network:
            kwargs["network"] = network
        if labels:
            kwargs["labels"] = labels

        c = self.client.containers.run(**kwargs)
        logger.info(f"Container created: {c.id}")
        return self._serialize_container(c)

    # -------------------------------------------------------------------------
    # IMAGES
    # -------------------------------------------------------------------------

    def list_images(self) -> List[Dict]:
        """Lista todas as imagens locais."""
        images = self.client.images.list()
        return [self._serialize_image(img) for img in images]

    def pull_image(self, repository: str, tag: str = "latest") -> Dict:
        """Faz o pull de uma imagem do registry."""
        logger.info(f"Pulling image: {repository}:{tag}")
        image = self.client.images.pull(repository, tag=tag)
        logger.info(f"Image pulled: {repository}:{tag}")
        return self._serialize_image(image)

    async def pull_image_stream(self, repository: str, tag: str = "latest") -> AsyncGenerator[str, None]:
        """Pull de imagem com streaming de progresso (SSE-friendly)."""
        for line in self.low_level.pull(repository, tag=tag, stream=True, decode=True):
            yield json.dumps(line)
            await asyncio.sleep(0)

    def remove_image(self, image_id: str, force: bool = False) -> bool:
        """Remove uma imagem local."""
        self.client.images.remove(image_id, force=force)
        logger.info(f"Image removed: {image_id}")
        return True

    def get_image_info(self, image_name: str) -> Dict:
        """Retorna informações detalhadas de uma imagem."""
        image = self.client.images.get(image_name)
        return self._serialize_image(image)

    # -------------------------------------------------------------------------
    # LOGS
    # -------------------------------------------------------------------------

    def get_container_logs(
        self,
        container_id: str,
        tail: int = 200,
        timestamps: bool = True,
    ) -> str:
        """Retorna os logs de um container."""
        c = self.client.containers.get(container_id)
        logs = c.logs(tail=tail, timestamps=timestamps)
        return logs.decode("utf-8", errors="replace")

    async def stream_container_logs(
        self,
        container_id: str,
        tail: int = 100,
        timestamps: bool = True,
    ) -> AsyncGenerator[str, None]:
        """Stream de logs de container (para SSE / WebSocket)."""
        c = self.client.containers.get(container_id)
        for log_line in c.logs(stream=True, follow=True, tail=tail, timestamps=timestamps):
            yield log_line.decode("utf-8", errors="replace")
            await asyncio.sleep(0)

    # -------------------------------------------------------------------------
    # STATS
    # -------------------------------------------------------------------------

    def get_container_stats(self, container_id: str) -> Dict:
        """Retorna stats instantâneos de CPU, RAM, rede e disco do container."""
        c = self.client.containers.get(container_id)
        raw = c.stats(stream=False)
        return self._parse_stats(raw, c.name)

    async def stream_container_stats(self, container_id: str) -> AsyncGenerator[Dict, None]:
        """Stream contínuo de stats do container."""
        c = self.client.containers.get(container_id)
        for raw in c.stats(stream=True, decode=True):
            yield self._parse_stats(raw, c.name)
            await asyncio.sleep(1)

    def _parse_stats(self, raw: Dict, container_name: str) -> Dict:
        """Parseia o payload raw de stats do Docker em métricas legíveis."""
        # CPU %
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
        cpu_percent = (cpu_delta / system_delta) * num_cpus * 100.0 if system_delta > 0 else 0.0

        # Memory
        mem_usage = raw["memory_stats"].get("usage", 0)
        mem_cache = raw["memory_stats"].get("stats", {}).get("cache", 0)
        mem_actual = mem_usage - mem_cache
        mem_limit = raw["memory_stats"].get("limit", 1)
        mem_percent = (mem_actual / mem_limit) * 100.0 if mem_limit > 0 else 0.0

        # Network
        net_rx, net_tx = 0, 0
        for iface_data in raw.get("networks", {}).values():
            net_rx += iface_data.get("rx_bytes", 0)
            net_tx += iface_data.get("tx_bytes", 0)

        # Block I/O
        blk_read, blk_write = 0, 0
        for bio in raw.get("blkio_stats", {}).get("io_service_bytes_recursive", []):
            if bio.get("op") == "read":
                blk_read += bio.get("value", 0)
            elif bio.get("op") == "write":
                blk_write += bio.get("value", 0)

        return {
            "container_name": container_name,
            "timestamp": raw.get("read", ""),
            "cpu": {
                "percent": round(cpu_percent, 2),
                "num_cpus": num_cpus,
            },
            "memory": {
                "usage_bytes": mem_actual,
                "usage_mb": round(mem_actual / 1024 / 1024, 2),
                "limit_bytes": mem_limit,
                "limit_mb": round(mem_limit / 1024 / 1024, 2),
                "percent": round(mem_percent, 2),
            },
            "network": {
                "rx_bytes": net_rx,
                "tx_bytes": net_tx,
                "rx_mb": round(net_rx / 1024 / 1024, 2),
                "tx_mb": round(net_tx / 1024 / 1024, 2),
            },
            "block_io": {
                "read_bytes": blk_read,
                "write_bytes": blk_write,
                "read_mb": round(blk_read / 1024 / 1024, 2),
                "write_mb": round(blk_write / 1024 / 1024, 2),
            },
        }

    # -------------------------------------------------------------------------
    # DOCKER COMPOSE
    # -------------------------------------------------------------------------

    def compose_deploy(
        self,
        app_id: str,
        compose_content: str,
        env_vars: Optional[Dict[str, str]] = None,
    ) -> Dict:
        """
        Faz o deploy de um app via docker-compose.
        Salva o compose em /opt/naybinho/apps/{app_id}/docker-compose.yml
        e executa `docker compose up -d`.
        """
        app_dir = COMPOSE_BASE_DIR / app_id
        app_dir.mkdir(parents=True, exist_ok=True)
        compose_file = app_dir / "docker-compose.yml"
        compose_file.write_text(compose_content, encoding="utf-8")

        # Escrever .env se fornecido
        if env_vars:
            env_file = app_dir / ".env"
            env_file.write_text(
                "\n".join(f"{k}={v}" for k, v in env_vars.items()), encoding="utf-8"
            )

        result = subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "up", "-d", "--remove-orphans"],
            capture_output=True,
            text=True,
            cwd=str(app_dir),
        )

        return {
            "app_id": app_id,
            "compose_file": str(compose_file),
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0,
        }

    def compose_down(self, app_id: str, volumes: bool = False) -> Dict:
        """Para e remove os serviços de um app via docker-compose."""
        app_dir = COMPOSE_BASE_DIR / app_id
        compose_file = app_dir / "docker-compose.yml"

        if not compose_file.exists():
            raise FileNotFoundError(f"Compose file not found for app: {app_id}")

        cmd = ["docker", "compose", "-f", str(compose_file), "down"]
        if volumes:
            cmd.append("-v")

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(app_dir))
        return {
            "app_id": app_id,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0,
        }

    def compose_pull(self, app_id: str) -> Dict:
        """Atualiza as imagens de um app via docker-compose."""
        app_dir = COMPOSE_BASE_DIR / app_id
        compose_file = app_dir / "docker-compose.yml"

        if not compose_file.exists():
            raise FileNotFoundError(f"Compose file not found for app: {app_id}")

        result = subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "pull"],
            capture_output=True,
            text=True,
            cwd=str(app_dir),
        )
        return {
            "app_id": app_id,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0,
        }

    def compose_logs(self, app_id: str, tail: int = 100) -> str:
        """Retorna logs de um app gerenciado via docker-compose."""
        app_dir = COMPOSE_BASE_DIR / app_id
        compose_file = app_dir / "docker-compose.yml"

        if not compose_file.exists():
            raise FileNotFoundError(f"Compose file not found for app: {app_id}")

        result = subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "logs", f"--tail={tail}", "--timestamps"],
            capture_output=True,
            text=True,
            cwd=str(app_dir),
        )
        return result.stdout + result.stderr

    # -------------------------------------------------------------------------
    # NETWORKS
    # -------------------------------------------------------------------------

    def list_networks(self) -> List[Dict]:
        """Lista todas as redes Docker."""
        networks = self.client.networks.list()
        return [self._serialize_network(n) for n in networks]

    def get_network(self, network_id: str) -> Dict:
        """Retorna detalhes de uma rede."""
        n = self.client.networks.get(network_id)
        return self._serialize_network(n)

    def create_network(
        self,
        name: str,
        driver: str = "bridge",
        subnet: Optional[str] = None,
        gateway: Optional[str] = None,
        labels: Optional[Dict] = None,
    ) -> Dict:
        """Cria uma nova rede Docker."""
        ipam_config = None
        if subnet:
            pool = docker.types.IPAMPool(subnet=subnet, gateway=gateway)
            ipam_config = docker.types.IPAMConfig(pool_configs=[pool])

        n = self.client.networks.create(
            name=name,
            driver=driver,
            ipam=ipam_config,
            labels=labels or {},
        )
        logger.info(f"Network created: {name}")
        return self._serialize_network(n)

    def remove_network(self, network_id: str) -> bool:
        """Remove uma rede Docker."""
        n = self.client.networks.get(network_id)
        n.remove()
        logger.info(f"Network removed: {network_id}")
        return True

    def connect_container_to_network(self, network_id: str, container_id: str) -> bool:
        """Conecta um container a uma rede."""
        n = self.client.networks.get(network_id)
        n.connect(container_id)
        return True

    def disconnect_container_from_network(self, network_id: str, container_id: str) -> bool:
        """Desconecta um container de uma rede."""
        n = self.client.networks.get(network_id)
        n.disconnect(container_id)
        return True

    # -------------------------------------------------------------------------
    # VOLUMES
    # -------------------------------------------------------------------------

    def list_volumes(self) -> List[Dict]:
        """Lista todos os volumes Docker."""
        volumes = self.client.volumes.list()
        return [self._serialize_volume(v) for v in volumes]

    def get_volume(self, volume_name: str) -> Dict:
        """Retorna detalhes de um volume."""
        v = self.client.volumes.get(volume_name)
        return self._serialize_volume(v)

    def create_volume(
        self,
        name: str,
        driver: str = "local",
        driver_opts: Optional[Dict] = None,
        labels: Optional[Dict] = None,
    ) -> Dict:
        """Cria um novo volume Docker."""
        v = self.client.volumes.create(
            name=name,
            driver=driver,
            driver_opts=driver_opts or {},
            labels=labels or {},
        )
        logger.info(f"Volume created: {name}")
        return self._serialize_volume(v)

    def remove_volume(self, volume_name: str, force: bool = False) -> bool:
        """Remove um volume Docker."""
        v = self.client.volumes.get(volume_name)
        v.remove(force=force)
        logger.info(f"Volume removed: {volume_name}")
        return True

    def prune_volumes(self) -> Dict:
        """Remove volumes não utilizados."""
        result = self.client.volumes.prune()
        return {"volumes_deleted": result.get("VolumesDeleted", []), "space_reclaimed": result.get("SpaceReclaimed", 0)}

    # -------------------------------------------------------------------------
    # HEALTH CHECK
    # -------------------------------------------------------------------------

    def get_container_health(self, container_id: str) -> Dict:
        """Retorna o status de health check do container."""
        c = self.client.containers.get(container_id)
        inspect = self.low_level.inspect_container(container_id)
        health = inspect.get("State", {}).get("Health", {})
        return {
            "container_id": container_id,
            "container_name": c.name,
            "status": c.status,
            "health_status": health.get("Status", "none"),
            "failing_streak": health.get("FailingStreak", 0),
            "last_log": health.get("Log", [{}])[-1] if health.get("Log") else None,
        }

    def health_check_all(self) -> List[Dict]:
        """Retorna health check de todos os containers em execução."""
        containers = self.client.containers.list()
        return [self.get_container_health(c.id) for c in containers]

    # -------------------------------------------------------------------------
    # EVENTOS DOCKER (SSE)
    # -------------------------------------------------------------------------

    async def stream_events(
        self,
        event_types: Optional[List[str]] = None,
    ) -> AsyncGenerator[Dict, None]:
        """
        Stream de eventos Docker em tempo real.
        Ideal para SSE (Server-Sent Events) no frontend.
        event_types ex: ['container', 'image', 'network', 'volume']
        """
        filters = {}
        if event_types:
            filters["type"] = event_types

        for event in self.client.events(decode=True, filters=filters):
            yield event
            await asyncio.sleep(0)

    # -------------------------------------------------------------------------
    # SYSTEM INFO
    # -------------------------------------------------------------------------

    def get_docker_info(self) -> Dict:
        """Retorna informações gerais do daemon Docker."""
        info = self.client.info()
        version = self.client.version()
        return {
            "version": version.get("Version", ""),
            "api_version": version.get("ApiVersion", ""),
            "containers_total": info.get("Containers", 0),
            "containers_running": info.get("ContainersRunning", 0),
            "containers_paused": info.get("ContainersPaused", 0),
            "containers_stopped": info.get("ContainersStopped", 0),
            "images": info.get("Images", 0),
            "mem_total_mb": round(info.get("MemTotal", 0) / 1024 / 1024, 2),
            "cpus": info.get("NCPU", 0),
            "os": info.get("OperatingSystem", ""),
            "kernel": info.get("KernelVersion", ""),
            "storage_driver": info.get("Driver", ""),
            "docker_root_dir": info.get("DockerRootDir", ""),
        }

    def system_prune(self, volumes: bool = False) -> Dict:
        """Remove recursos Docker não utilizados (containers, imagens, networks)."""
        result = self.client.containers.prune()
        images_result = self.client.images.prune()
        networks_result = self.client.networks.prune()
        volumes_result = self.client.volumes.prune() if volumes else {}
        return {
            "containers_deleted": result.get("ContainersDeleted", []),
            "images_deleted": [i.get("Deleted") for i in images_result.get("ImagesDeleted", []) if i.get("Deleted")],
            "networks_deleted": networks_result.get("NetworksDeleted", []),
            "volumes_deleted": volumes_result.get("VolumesDeleted", []) if volumes else [],
            "space_reclaimed_bytes": (
                result.get("SpaceReclaimed", 0)
                + images_result.get("SpaceReclaimed", 0)
                + networks_result.get("SpaceReclaimed", 0)
                + (volumes_result.get("SpaceReclaimed", 0) if volumes else 0)
            ),
        }

    # -------------------------------------------------------------------------
    # SERIALIZERS
    # -------------------------------------------------------------------------

    def _serialize_container(self, c: Container) -> Dict:
        c.reload()
        inspect = self.low_level.inspect_container(c.id)
        ports = inspect.get("NetworkSettings", {}).get("Ports", {})
        return {
            "id": c.short_id,
            "full_id": c.id,
            "name": c.name,
            "image": c.image.tags[0] if c.image.tags else c.image.short_id,
            "status": c.status,
            "state": inspect.get("State", {}),
            "created": inspect.get("Created", ""),
            "started": inspect.get("State", {}).get("StartedAt", ""),
            "ports": ports,
            "labels": c.labels,
            "mounts": [
                {
                    "source": m.get("Source", ""),
                    "destination": m.get("Destination", ""),
                    "mode": m.get("Mode", ""),
                    "rw": m.get("RW", True),
                }
                for m in inspect.get("Mounts", [])
            ],
            "networks": list(inspect.get("NetworkSettings", {}).get("Networks", {}).keys()),
            "restart_policy": inspect.get("HostConfig", {}).get("RestartPolicy", {}).get("Name", ""),
            "env": inspect.get("Config", {}).get("Env", []),
            "command": inspect.get("Config", {}).get("Cmd", []),
            "health": inspect.get("State", {}).get("Health", {}).get("Status", "none"),
        }

    def _serialize_image(self, img: Image) -> Dict:
        return {
            "id": img.short_id,
            "full_id": img.id,
            "tags": img.tags,
            "size_mb": round(img.attrs.get("Size", 0) / 1024 / 1024, 2),
            "created": img.attrs.get("Created", ""),
            "architecture": img.attrs.get("Architecture", ""),
            "os": img.attrs.get("Os", ""),
            "labels": img.labels,
        }

    def _serialize_network(self, n: Network) -> Dict:
        return {
            "id": n.short_id,
            "full_id": n.id,
            "name": n.name,
            "driver": n.attrs.get("Driver", ""),
            "scope": n.attrs.get("Scope", ""),
            "ipam": n.attrs.get("IPAM", {}),
            "internal": n.attrs.get("Internal", False),
            "containers": list(n.attrs.get("Containers", {}).keys()),
            "labels": n.attrs.get("Labels", {}),
            "created": n.attrs.get("Created", ""),
        }

    def _serialize_volume(self, v: Volume) -> Dict:
        return {
            "name": v.name,
            "driver": v.attrs.get("Driver", "local"),
            "mountpoint": v.attrs.get("Mountpoint", ""),
            "created": v.attrs.get("CreatedAt", ""),
            "labels": v.attrs.get("Labels", {}),
            "scope": v.attrs.get("Scope", "local"),
            "options": v.attrs.get("Options", {}),
        }


# Singleton
_docker_service: Optional[DockerService] = None


def get_docker_service() -> DockerService:
    """Retorna a instância singleton do DockerService."""
    global _docker_service
    if _docker_service is None:
        _docker_service = DockerService()
    return _docker_service
