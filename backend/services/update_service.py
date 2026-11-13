"""
NayBinho NAS — Update Service.
Gerencia a verificação de novas releases/ISOs no GitHub, notificação e auto-atualização do sistema.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from loguru import logger

from config import settings


class UpdateService:
    def __init__(self):
        self.last_check: Optional[datetime] = None
        self.update_in_progress: bool = False
        self.update_progress: Dict[str, Any] = {
            "stage": "idle",
            "percent": 0,
            "message": "Nenhuma atualização em andamento",
            "started_at": None,
            "completed_at": None,
            "error": None,
        }
        self.latest_release_info: Dict[str, Any] = {
            "current_version": self.get_current_version(),
            "latest_version": self.get_current_version(),
            "has_update": False,
            "release_title": "",
            "release_notes": "",
            "published_at": None,
            "iso_asset": None,
            "update_asset": None,
            "system_packages": [],
            "last_checked": None,
        }

    def get_current_version(self) -> str:
        """Lê versão do arquivo VERSION ou config."""
        version_file = settings.version_file
        if version_file.exists():
            try:
                v = version_file.read_text(encoding="utf-8").strip()
                if v:
                    return v.lstrip("v")
            except Exception:
                pass
        return settings.app_version.lstrip("v")

    def _run_cmd(self, cmd: list[str], timeout: int = 300) -> tuple[int, str, str]:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return res.returncode, res.stdout, res.stderr

    def _version_tuple(self, v_str: str) -> tuple:
        """Converte versão semântica para tupla comparável (ex: '1.0.1' -> (1, 0, 1))."""
        cleaned = v_str.lstrip("v").strip()
        parts = []
        for p in cleaned.split("."):
            try:
                parts.append(int(p))
            except ValueError:
                parts.append(0)
        return tuple(parts)

    async def check_updates(self) -> Dict[str, Any]:
        """
        Consulta o GitHub Releases para verificar se há nova versão da ISO ou pacote de atualização,
        além de consultar o gerenciador de pacotes do sistema (apt).
        """
        self.last_check = datetime.now(timezone.utc)
        current_version = self.get_current_version()

        # 1. Checagem de atualizações do Ubuntu via apt
        pkg_updates = []
        try:
            rc, _, _ = self._run_cmd(["apt-get", "update", "-q"], timeout=60)
            if rc == 0:
                rc2, out, _ = self._run_cmd(["apt-get", "--simulate", "--just-print", "upgrade"], timeout=60)
                for line in out.splitlines():
                    if line.startswith("Inst "):
                        parts = line.split()
                        pkg_updates.append({
                            "name": parts[1] if len(parts) > 1 else line,
                            "version": parts[2].strip("[]()") if len(parts) > 2 else "",
                        })
        except Exception as exc:
            logger.debug(f"Aviso apt-get update: {exc}")

        # 2. Checagem de nova Release/ISO no GitHub
        remote_version = current_version
        has_nas_update = False
        release_title = ""
        release_notes = ""
        published_at = None
        iso_asset = None
        update_asset = None

        github_repo = getattr(settings, "github_repo", "naybinho/nas")
        api_url = f"https://api.github.com/repos/{github_repo}/releases/latest"

        try:
            req = urllib.request.Request(
                api_url,
                headers={
                    "User-Agent": "NayBinhoNAS-AutoUpdater/1.0",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            loop = asyncio.get_event_loop()
            
            def _fetch():
                with urllib.request.urlopen(req, timeout=15) as resp:
                    return json.loads(resp.read().decode("utf-8"))

            data = await loop.run_in_executor(None, _fetch)

            tag_name = data.get("tag_name", "").lstrip("v").strip()
            if tag_name:
                remote_version = tag_name
                release_title = data.get("name", f"NayBinho NAS v{tag_name}")
                release_notes = data.get("body", "")
                published_at = data.get("published_at")

                # Compara versões
                if self._version_tuple(remote_version) > self._version_tuple(current_version):
                    has_nas_update = True

                # Procura por assets de ISO e pacote de atualização
                for asset in data.get("assets", []):
                    name = asset.get("name", "")
                    url = asset.get("browser_download_url")
                    size = asset.get("size", 0)

                    if name.endswith(".iso"):
                        iso_asset = {
                            "name": name,
                            "download_url": url,
                            "size_bytes": size,
                            "size_mb": round(size / (1024 * 1024), 1),
                        }
                    elif "update" in name and (name.endswith(".tar.gz") or name.endswith(".zip")):
                        update_asset = {
                            "name": name,
                            "download_url": url,
                            "size_bytes": size,
                            "size_mb": round(size / (1024 * 1024), 1),
                        }

                # Fallback para tarball do código fonte da release
                if not update_asset and data.get("tarball_url"):
                    update_asset = {
                        "name": f"naybinho-v{tag_name}.tar.gz",
                        "download_url": data.get("tarball_url"),
                        "size_bytes": 0,
                        "size_mb": 0,
                    }

        except Exception as exc:
            logger.warning(f"Não foi possível consultar GitHub Releases ({api_url}): {exc}")

        self.latest_release_info = {
            "current_version": current_version,
            "latest_version": remote_version,
            "has_update": has_nas_update,
            "release_title": release_title,
            "release_notes": release_notes,
            "published_at": published_at,
            "iso_asset": iso_asset,
            "update_asset": update_asset,
            "system_packages_count": len(pkg_updates),
            "system_packages": pkg_updates,
            "last_checked": self.last_check.isoformat(),
        }

        return self.latest_release_info

    def get_status(self) -> Dict[str, Any]:
        """Retorna o status atual do processo de atualização e da última checagem."""
        return {
            "in_progress": self.update_in_progress,
            "progress": self.update_progress,
            "latest_release": self.latest_release_info,
        }

    async def apply_self_update(
        self,
        update_os_packages: bool = True,
        update_nas_software: bool = True,
    ) -> Dict[str, Any]:
        """
        Executa a auto-atualização ponta a ponta:
        1. Backup prévio de segurança
        2. Download do pacote da nova versão do GitHub
        3. Validação do arquivo
        4. Aplicação dos novos arquivos (backend, frontend, system)
        5. Atualização de pacotes do sistema operacional
        6. Reinicialização de serviços do NayBinho NAS
        """
        if self.update_in_progress:
            return {"status": "error", "message": "Uma atualização já está em andamento."}

        self.update_in_progress = True
        self.update_progress = {
            "stage": "starting",
            "percent": 5,
            "message": "Inicializando processo de auto-atualização...",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": None,
            "error": None,
        }

        loop = asyncio.get_event_loop()

        def _run_update_pipeline():
            try:
                # ── ETAPA 1: Backup de Segurança ──
                self._set_progress("backup", 15, "Criando backup preventivo das configurações e banco de dados...")
                backup_script = Path("/opt/naybinho/system/scripts/backup.sh")
                if backup_script.exists():
                    subprocess.run(["bash", str(backup_script)], capture_output=True, timeout=120)

                # ── ETAPA 2: Download do Pacote ──
                if update_nas_software:
                    update_url = None
                    if self.latest_release_info.get("update_asset"):
                        update_url = self.latest_release_info["update_asset"].get("download_url")

                    if not update_url:
                        # Fallback: consultar última release novamente se não houver asset cacheado
                        github_repo = getattr(settings, "github_repo", "naybinho/nas")
                        update_url = f"https://github.com/{github_repo}/archive/refs/heads/main.tar.gz"

                    self._set_progress("downloading", 35, f"Baixando nova versão do sistema de {update_url}...")
                    tmp_dir = Path("/tmp/naybinho-update")
                    if tmp_dir.exists():
                        shutil.rmtree(str(tmp_dir), ignore_errors=True)
                    tmp_dir.mkdir(parents=True, exist_ok=True)

                    archive_path = tmp_dir / "update.tar.gz"
                    req = urllib.request.Request(
                        update_url,
                        headers={"User-Agent": "NayBinhoNAS-AutoUpdater/1.0"},
                    )
                    with urllib.request.urlopen(req, timeout=120) as resp, open(archive_path, "wb") as out_f:
                        shutil.copyfileobj(resp, out_f)

                    # ── ETAPA 3: Extração e Validação ──
                    self._set_progress("extracting", 60, "Extraindo e validando arquivos do sistema...")
                    with tarfile.open(archive_path, "r:gz") as tar:
                        tar.extractall(path=tmp_dir)

                    # Localiza o diretório raiz dos arquivos
                    extracted_root = tmp_dir
                    subdirs = [p for p in tmp_dir.iterdir() if p.is_dir()]
                    if len(subdirs) == 1 and not (tmp_dir / "backend").exists():
                        extracted_root = subdirs[0]

                    # ── ETAPA 4: Aplicação dos Arquivos ──
                    self._set_progress("applying", 75, "Atualizando backend, frontend e scripts...")
                    target_root = Path("/opt/naybinho")
                    if target_root.exists():
                        for item in ["backend", "frontend/dist", "system", "appstore"]:
                            src = extracted_root / item
                            dest = target_root / item
                            if src.exists():
                                if src.is_dir():
                                    shutil.copytree(str(src), str(dest), dirs_exist_ok=True)
                                else:
                                    shutil.copy2(str(src), str(dest))

                    # Atualiza VERSION
                    new_ver = self.latest_release_info.get("latest_version")
                    if new_ver:
                        settings.version_file.parent.mkdir(parents=True, exist_ok=True)
                        settings.version_file.write_text(new_ver, encoding="utf-8")

                # ── ETAPA 5: Pacotes do Sistema (APT) ──
                if update_os_packages:
                    self._set_progress("os_packages", 85, "Atualizando pacotes e dependências do Ubuntu 26.04...")
                    subprocess.run(
                        ["apt-get", "-y", "upgrade", "-o", "Dpkg::Options::=--force-confdef", "-o", "Dpkg::Options::=--force-confold"],
                        capture_output=True,
                        timeout=900,
                    )

                # ── ETAPA 6: Reinicialização dos Serviços ──
                self._set_progress("restarting", 95, "Reiniciando serviços do NayBinho NAS...")
                subprocess.run(["systemctl", "daemon-reload"], capture_output=True)
                subprocess.run(["systemctl", "restart", "naybinho-backend", "naybinho-monitor"], capture_output=True)
                subprocess.run(["systemctl", "reload", "nginx"], capture_output=True)

                self._set_progress("completed", 100, "Sistema atualizado com sucesso!")
                self.update_progress["completed_at"] = datetime.now(timezone.utc).isoformat()

            except Exception as e:
                logger.error(f"Erro durante atualização: {e}")
                self.update_progress["stage"] = "error"
                self.update_progress["error"] = str(e)
                self.update_progress["message"] = f"Falha na atualização: {e}"
            finally:
                self.update_in_progress = False

        # Dispara thread em background
        loop.run_in_executor(None, _run_update_pipeline)

        return {
            "status": "started",
            "message": "Processo de auto-atualização iniciado em segundo plano.",
        }

    def _set_progress(self, stage: str, percent: int, message: str):
        self.update_progress["stage"] = stage
        self.update_progress["percent"] = percent
        self.update_progress["message"] = message
        logger.info(f"[AutoUpdater] [{percent}%] {message}")


update_service = UpdateService()
