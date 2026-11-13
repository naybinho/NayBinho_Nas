"""
NayBinho NAS — Apps Store Service
Gerencia a loja de aplicações: multi-repositórios, fontes remotas (CasaOS/ZimaOS/PlayStore),
sincronização de catálogos, instalação, remoção, atualização e status de apps.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("naybinho.apps_service")

# Diretórios padrão
BASE_DIR = Path(__file__).parent.parent
SERVICES_DIR = Path(__file__).parent
CATALOG_PATH = Path("/opt/naybinho/appstore/catalog.json")
SOURCES_PATH = Path("/opt/naybinho/appstore/sources.json")
CACHE_DIR = Path("/opt/naybinho/appstore/cache")
APPS_DIR = Path("/opt/naybinho/apps")
INSTALLED_DB = Path("/opt/naybinho/appstore/installed.json")

# Permite fallback para desenvolvimento local no repositório
if not CATALOG_PATH.exists():
    fallback_cat = SERVICES_DIR / "apps_catalog.json"
    if fallback_cat.exists():
        CATALOG_PATH = fallback_cat

if not SOURCES_PATH.exists():
    fallback_src = SERVICES_DIR / "store_sources.json"
    if fallback_src.exists():
        SOURCES_PATH = fallback_src

if not CACHE_DIR.exists():
    CACHE_DIR = BASE_DIR / "data" / "stores_cache"


def _ensure_dirs():
    try:
        APPS_DIR.mkdir(parents=True, exist_ok=True)
        INSTALLED_DB.parent.mkdir(parents=True, exist_ok=True)
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        SOURCES_PATH.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.debug(f"Directory creation note: {e}")


def _load_installed() -> Dict[str, Any]:
    if INSTALLED_DB.exists():
        try:
            with open(INSTALLED_DB, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def _save_installed(data: Dict[str, Any]):
    try:
        INSTALLED_DB.parent.mkdir(parents=True, exist_ok=True)
        with open(INSTALLED_DB, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Error saving installed apps db: {e}")


class AppsService:
    """Serviço de gerenciamento da App Store Multi-Repositório do NayBinho NAS."""

    def __init__(self):
        _ensure_dirs()
        self._sources: Optional[List[Dict[str, Any]]] = None
        self._cached_catalog: Optional[List[Dict[str, Any]]] = None

    # -------------------------------------------------------------------------
    # FONTES / REPOSITÓRIOS (MULTI-STORE)
    # -------------------------------------------------------------------------

    def get_sources(self) -> List[Dict[str, Any]]:
        """Carrega a lista de fontes configuradas."""
        if SOURCES_PATH.exists():
            try:
                with open(SOURCES_PATH, "r", encoding="utf-8") as f:
                    self._sources = json.load(f)
                    return self._sources
            except Exception as e:
                logger.error(f"Failed to read sources from {SOURCES_PATH}: {e}")

        # Default fontes
        self._sources = [
            {
                "id": "naybinho_official",
                "name": "NayBinho Oficial",
                "url": "local",
                "description": "Loja nativa oficial otimizada para o NayBinho NAS com suporte a hardware e transcodificação.",
                "enabled": True,
                "type": "native",
                "icon": "⚡",
                "last_sync": datetime.now(timezone.utc).isoformat(),
                "app_count": 107,
                "status": "ready",
            },
            {
                "id": "play_store",
                "name": "CasaOS Play Store",
                "url": "https://play.cuse.eu.org/store.json",
                "description": "Repositório comunitário Play Store com centenas de aplicações e utilitários.",
                "enabled": True,
                "type": "casaos",
                "icon": "🎮",
                "last_sync": None,
                "app_count": 0,
                "status": "pending_sync",
            },
            {
                "id": "big_bear_casaos",
                "name": "BigBear CasaOS Store",
                "url": "https://cdn.jsdelivr.net/gh/bigbeartechworld/big-bear-casaos@gh-pages/store.json",
                "description": "Grande biblioteca de aplicações mantida pelo BigBearTechWorld.",
                "enabled": True,
                "type": "casaos",
                "icon": "🐻",
                "last_sync": None,
                "app_count": 0,
                "status": "pending_sync",
            },
            {
                "id": "zima_store",
                "name": "Zima AppStore",
                "url": "https://chicohaager.github.io/zima-appstore/store.json",
                "description": "Repositório de aplicações curadas para ZimaOS / CasaOS mantido por Chico Haager.",
                "enabled": True,
                "type": "casaos",
                "icon": "❄️",
                "last_sync": None,
                "app_count": 0,
                "status": "pending_sync",
            },
        ]
        self._save_sources()
        return self._sources

    def _save_sources(self):
        """Persiste as fontes no arquivo de configuração."""
        try:
            SOURCES_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(SOURCES_PATH, "w", encoding="utf-8") as f:
                json.dump(self._sources, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save sources to {SOURCES_PATH}: {e}")

    def add_source(self, name: str, url: str, description: str = "", store_type: str = "casaos", icon: str = "📦") -> Dict[str, Any]:
        """Adiciona uma nova loja/fonte ao catálogo."""
        sources = self.get_sources()
        source_id = re.sub(r"[^a-zA-Z0-9_-]", "_", name.lower().strip())
        if any(s["id"] == source_id or s["url"] == url for s in sources if s["url"] != "local"):
            raise ValueError(f"Fonte com este nome ou URL já existe.")

        new_source = {
            "id": source_id,
            "name": name.strip(),
            "url": url.strip(),
            "description": description.strip() or f"Loja personalizada {name}",
            "enabled": True,
            "type": store_type,
            "icon": icon or "📦",
            "last_sync": None,
            "app_count": 0,
            "status": "pending_sync",
        }
        sources.append(new_source)
        self._save_sources()
        # Sincroniza imediatamente a nova fonte
        self.sync_source(source_id)
        return new_source

    def update_source(self, source_id: str, enabled: Optional[bool] = None, name: Optional[str] = None) -> Dict[str, Any]:
        """Ativa/desativa ou altera dados de uma fonte."""
        sources = self.get_sources()
        for s in sources:
            if s["id"] == source_id:
                if enabled is not None:
                    s["enabled"] = enabled
                if name:
                    s["name"] = name.strip()
                self._save_sources()
                self._cached_catalog = None
                return s
        raise ValueError(f"Fonte '{source_id}' não encontrada.")

    def remove_source(self, source_id: str) -> bool:
        """Remove uma fonte customizada (fontes nativas protegidas)."""
        if source_id == "naybinho_official":
            raise ValueError("A loja oficial NayBinho não pode ser removida.")

        sources = self.get_sources()
        initial_len = len(sources)
        self._sources = [s for s in sources if s["id"] != source_id]
        if len(self._sources) < initial_len:
            self._save_sources()
            # Deletar cache
            cache_file = CACHE_DIR / f"{source_id}.json"
            if cache_file.exists():
                cache_file.unlink()
            self._cached_catalog = None
            return True
        return False

    # -------------------------------------------------------------------------
    # SINCRONIZAÇÃO E PARSER DE STORE.JSON
    # -------------------------------------------------------------------------

    def sync_source(self, source_id: str) -> Dict[str, Any]:
        """Busca o store.json remoto ou arquivo zip da fonte e armazena em cache."""
        sources = self.get_sources()
        source = next((s for s in sources if s["id"] == source_id), None)
        if not source:
            raise ValueError(f"Fonte '{source_id}' não encontrada.")

        if source["url"] == "local":
            # Loja local nativa
            local_catalog = self._load_local_catalog()
            source["app_count"] = len(local_catalog)
            source["last_sync"] = datetime.now(timezone.utc).isoformat()
            source["status"] = "ready"
            self._save_sources()
            self._cached_catalog = None
            return {"source_id": source_id, "success": True, "count": len(local_catalog)}

        logger.info(f"Sincronizando fonte {source['name']} ({source['url']})...")
        source["status"] = "syncing"
        self._save_sources()

        is_zip = (
            source["url"].lower().endswith(".zip")
            or source.get("type") in ("zip", "casaos_zip")
            or "/archive/" in source["url"]
        )

        try:
            req = urllib.request.Request(
                source["url"],
                headers={
                    "User-Agent": "NayBinhoNAS/1.0 (HomeLab; Linux x86_64)",
                    "Accept": "*/*",
                },
            )
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw_bytes = resp.read()

            if is_zip:
                apps = self._parse_zip_store(raw_bytes, source)
            else:
                parsed_json = json.loads(raw_bytes.decode("utf-8"))
                apps = self._parse_external_store(parsed_json, source)

            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_file = CACHE_DIR / f"{source_id}.json"
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(apps, f, indent=2, ensure_ascii=False)

            source["status"] = "ready"
            source["app_count"] = len(apps)
            source["last_sync"] = datetime.now(timezone.utc).isoformat()
            self._save_sources()
            self._cached_catalog = None
            logger.info(f"Fonte {source['name']} sincronizada: {len(apps)} aplicativos carregados.")
            return {"source_id": source_id, "success": True, "count": len(apps)}

        except Exception as e:
            logger.error(f"Erro ao sincronizar fonte {source['name']}: {e}")
            source["status"] = "error"
            source["error_message"] = str(e)
            self._save_sources()
            return {"source_id": source_id, "success": False, "error": str(e)}

    def _parse_zip_store(self, zip_bytes: bytes, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extrai repositório compactado em ZIP (como GitHub master.zip) e extrai stacks."""
        import io
        import zipfile
        try:
            import yaml
        except ImportError:
            yaml = None

        parsed_list: List[Dict[str, Any]] = []

        try:
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                # 1. Verifica se existe store.json dentro do zip
                store_json_files = [n for n in zf.namelist() if n.endswith("store.json")]
                if store_json_files:
                    for s_name in store_json_files:
                        try:
                            content = zf.read(s_name).decode("utf-8")
                            data = json.loads(content)
                            apps = self._parse_external_store(data, source)
                            if apps:
                                return apps
                        except Exception as e:
                            logger.debug(f"Failed parsing {s_name} in zip: {e}")

                # 2. Percorre pastas Apps/<app_id>/docker-compose.yml
                compose_files = [
                    n for n in zf.namelist()
                    if "/Apps/" in n and (n.endswith("docker-compose.yml") or n.endswith("docker-compose.yaml"))
                ]

                for c_path in compose_files:
                    try:
                        parts = c_path.split("/")
                        apps_idx = parts.index("Apps")
                        if len(parts) > apps_idx + 1:
                            app_folder = parts[apps_idx + 1]
                        else:
                            continue

                        compose_text = zf.read(c_path).decode("utf-8")
                        meta: Dict[str, Any] = {}
                        if yaml:
                            try:
                                doc = yaml.safe_load(compose_text)
                                if isinstance(doc, dict):
                                    meta = doc.get("x-casaos", {}) or {}
                            except Exception:
                                meta = {}

                        # Título
                        title = meta.get("title")
                        if isinstance(title, dict):
                            name = title.get("pt_br") or title.get("en_us") or next(iter(title.values()), app_folder)
                        elif isinstance(title, str) and title:
                            name = title
                        else:
                            name = app_folder.replace("-", " ").title()

                        # Descrição
                        desc = meta.get("description") or meta.get("tagline") or ""
                        if isinstance(desc, dict):
                            description = desc.get("pt_br") or desc.get("en_us") or next(iter(desc.values()), "")
                        else:
                            description = str(desc)

                        # Ícone
                        icon = meta.get("icon") or f"https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/png/{app_folder}.png"
                        category = meta.get("category") or "Utility"
                        if isinstance(category, list):
                            category = category[0] if category else "Utility"
                        elif isinstance(category, dict):
                            category = category.get("en_us") or next(iter(category.values()), "Utility")

                        parsed_list.append({
                            "id": f"{source['id']}_{app_folder.lower()}",
                            "original_id": app_folder.lower(),
                            "name": str(name),
                            "description": str(description),
                            "category": str(category).capitalize(),
                            "version": str(meta.get("version", "latest")),
                            "icon": str(icon),
                            "icon_url": str(icon),
                            "docker_image": "",
                            "docker_compose": compose_text,
                            "ports": meta.get("ports", []),
                            "volumes": meta.get("volumes", []),
                            "source_id": source["id"],
                            "source_name": source["name"],
                            "tags": meta.get("tags", [app_folder]),
                            "developer": meta.get("developer", ""),
                            "homepage": meta.get("homepage", ""),
                        })
                    except Exception as e:
                        logger.debug(f"Error parsing app in zip {c_path}: {e}")

        except Exception as e:
            logger.error(f"Erro ao processar arquivo ZIP da fonte {source['name']}: {e}")

        return parsed_list

    def sync_all_sources(self) -> List[Dict[str, Any]]:
        """Sincroniza todas as fontes ativas."""
        sources = self.get_sources()
        results = []
        for s in sources:
            if s.get("enabled", True):
                try:
                    res = self.sync_source(s["id"])
                    results.append(res)
                except Exception as e:
                    results.append({"source_id": s["id"], "success": False, "error": str(e)})
        self._cached_catalog = None
        return results

    def _parse_external_store(self, data: Any, source: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Interpreta schemas de lojas CasaOS, ZimaOS ou genéricas em um formato unificado."""
        raw_apps = []
        if isinstance(data, dict):
            if "apps" in data:
                raw_apps = data["apps"]
            elif "list" in data:
                raw_apps = data["list"]
            else:
                raw_apps = list(data.values())
        elif isinstance(data, list):
            raw_apps = data

        parsed_list: List[Dict[str, Any]] = []

        for item in raw_apps:
            if not isinstance(item, dict):
                continue

            app_id = str(item.get("name") or item.get("id") or item.get("app_id") or "").lower()
            if not app_id:
                continue

            # Nome / Título (pode ser dict multilíngue ou string)
            title = item.get("title")
            if isinstance(title, dict):
                name = title.get("pt_br") or title.get("en_us") or next(iter(title.values()), app_id)
            elif isinstance(title, str) and title:
                name = title
            else:
                name = item.get("name") or app_id

            # Descrição / Tagline
            desc = item.get("description") or item.get("tagline") or ""
            if isinstance(desc, dict):
                description = desc.get("pt_br") or desc.get("en_us") or next(iter(desc.values()), "")
            elif isinstance(desc, str):
                description = desc
            else:
                description = ""

            # Ícone
            icon = item.get("icon") or item.get("icon_url") or "https://raw.githubusercontent.com/walkxcode/dashboard-icons/main/png/docker.png"

            # Categoria
            cat = item.get("category") or "General"
            if isinstance(cat, list):
                category = cat[0] if cat else "General"
            elif isinstance(cat, dict):
                category = cat.get("en_us") or next(iter(cat.values()), "General")
            else:
                category = str(cat)

            # Docker Compose ou Imagem
            compose_raw = item.get("compose") or item.get("docker_compose") or ""
            if isinstance(compose_raw, dict):
                try:
                    import yaml
                    compose_str = yaml.dump(compose_raw)
                except Exception:
                    compose_str = json.dumps(compose_raw)
            elif isinstance(compose_raw, str):
                compose_str = compose_raw
            else:
                compose_str = ""

            image = item.get("image") or item.get("docker_image") or ""
            ports = item.get("ports", [])
            volumes = item.get("volumes", [])

            tags = item.get("tags", [])
            if not isinstance(tags, list):
                tags = [str(tags)]

            parsed_list.append({
                "id": f"{source['id']}_{app_id}",
                "original_id": app_id,
                "name": str(name),
                "description": str(description),
                "category": category.capitalize(),
                "version": str(item.get("version", "latest")),
                "icon": str(icon),
                "icon_url": str(icon),
                "docker_image": str(image),
                "docker_compose": compose_str,
                "ports": ports if isinstance(ports, list) else [],
                "volumes": volumes if isinstance(volumes, list) else [],
                "source_id": source["id"],
                "source_name": source["name"],
                "tags": tags,
                "homepage": item.get("homepage", ""),
                "developer": item.get("developer", ""),
            })

        return parsed_list

    # -------------------------------------------------------------------------
    # CATÁLOGO UNIFICADO
    # -------------------------------------------------------------------------

    def _load_local_catalog(self) -> List[Dict[str, Any]]:
        """Carrega o catálogo local do NayBinho NAS."""
        paths_to_try = [
            CATALOG_PATH,
            SERVICES_DIR / "apps_catalog.json",
            BASE_DIR / "appstore" / "catalog.json",
        ]
        for p in paths_to_try:
            if p.exists():
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        for item in data:
                            item.setdefault("source_id", "naybinho_official")
                            item.setdefault("source_name", "NayBinho Oficial")
                        return data
                except Exception as e:
                    logger.error(f"Failed to read local catalog at {p}: {e}")
        return []

    def get_catalog(self, source_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retorna todos os aplicativos de todas as fontes ativas agregadas."""
        if self._cached_catalog is not None and not source_filter:
            return self._cached_catalog

        aggregated: List[Dict[str, Any]] = []
        sources = self.get_sources()

        for s in sources:
            if not s.get("enabled", True):
                continue
            if source_filter and source_filter != "all" and s["id"] != source_filter:
                continue

            if s["id"] == "naybinho_official":
                local_apps = self._load_local_catalog()
                aggregated.extend(local_apps)
            else:
                cache_file = CACHE_DIR / f"{s['id']}.json"
                if cache_file.exists():
                    try:
                        with open(cache_file, "r", encoding="utf-8") as f:
                            external_apps = json.load(f)
                            aggregated.extend(external_apps)
                    except Exception as e:
                        logger.error(f"Error reading cache for source {s['id']}: {e}")

        # Anotar status de instalação
        installed = _load_installed()
        for app in aggregated:
            app_id = app["id"]
            orig_id = app.get("original_id", app_id)
            is_inst = (app_id in installed) or (orig_id in installed)
            app["installed"] = is_inst
            app["is_installed"] = is_inst
            app["installed_status"] = installed.get(app_id, {}).get("status", "not_installed")

        if not source_filter or source_filter == "all":
            self._cached_catalog = aggregated

        return aggregated

    def get_app_by_id(self, app_id: str) -> Optional[Dict[str, Any]]:
        """Busca um app pelo seu ID unificado ou ID original."""
        catalog = self.get_catalog()
        for app in catalog:
            if app.get("id") == app_id or app.get("original_id") == app_id:
                return app
        return None

    def search_apps(
        self,
        query: str = "",
        category: str = "",
        source_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Filtra catálogo com busca, categoria e fonte."""
        results = self.get_catalog(source_filter=source_id)
        if query:
            q = query.lower()
            results = [
                a for a in results
                if q in a.get("name", "").lower()
                or q in a.get("description", "").lower()
                or q in a.get("id", "").lower()
            ]
        if category and category.lower() != "todos" and category.lower() != "all":
            results = [a for a in results if a.get("category", "").lower() == category.lower()]
        if tags:
            results = [a for a in results if any(t in a.get("tags", []) for t in tags)]
        return results

    # -------------------------------------------------------------------------
    # INSTALAÇÃO & DESINSTALAÇÃO
    # -------------------------------------------------------------------------

    def install_app(
        self,
        app_id: str,
        custom_env: Optional[Dict[str, str]] = None,
        custom_ports: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Instala o aplicativo criando sua pasta compose e executando docker compose up."""
        app = self.get_app_by_id(app_id)
        if not app:
            raise ValueError(f"App '{app_id}' não encontrado em nenhuma loja ativa.")

        installed = _load_installed()
        clean_id = re.sub(r"[^a-zA-Z0-9_-]", "-", app_id)
        app_dir = APPS_DIR / clean_id
        app_dir.mkdir(parents=True, exist_ok=True)

        compose_content = app.get("docker_compose", "").strip()
        if not compose_content:
            compose_content = self._generate_minimal_compose(app)

        compose_file = app_dir / "docker-compose.yml"
        compose_file.write_text(compose_content, encoding="utf-8")

        env_vars = {**app.get("environment", {}), **(custom_env or {})}
        if env_vars:
            env_content = "\n".join(f"{k}={v}" for k, v in env_vars.items())
            (app_dir / ".env").write_text(env_content, encoding="utf-8")

        logger.info(f"Instalando app: {clean_id} em {app_dir}")
        result = subprocess.run(
            ["docker", "compose", "-f", str(compose_file), "up", "-d", "--remove-orphans", "--pull", "always"],
            capture_output=True,
            text=True,
            cwd=str(app_dir),
        )

        success = result.returncode == 0
        installed[app_id] = {
            "id": app_id,
            "name": app.get("name", app_id),
            "version": app.get("version", "latest"),
            "category": app.get("category", ""),
            "icon": app.get("icon", ""),
            "source_id": app.get("source_id", "naybinho_official"),
            "source_name": app.get("source_name", "NayBinho Oficial"),
            "app_dir": str(app_dir),
            "compose_file": str(compose_file),
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "status": "running" if success else "error",
            "error": result.stderr if not success else None,
        }
        _save_installed(installed)

        return {
            "app_id": app_id,
            "success": success,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "app_dir": str(app_dir),
        }

    def _generate_minimal_compose(self, app: Dict[str, Any]) -> str:
        """Gera compose básico caso o repositório forneça apenas a imagem."""
        image = app.get("docker_image") or f"{app['id']}:latest"
        safe_id = re.sub(r"[^a-zA-Z0-9_-]", "", app.get("original_id", app["id"]))
        lines = [
            "version: '3.8'",
            "services:",
            f"  {safe_id}:",
            f"    image: {image}",
            "    container_name: " + safe_id,
            "    restart: unless-stopped",
        ]
        ports = app.get("ports", [])
        if ports:
            lines.append("    ports:")
            for p in ports:
                lines.append(f'      - "{p}"')

        volumes = app.get("volumes", [])
        if volumes:
            lines.append("    volumes:")
            for v in volumes:
                lines.append(f'      - "{v}"')

        lines.extend([
            "networks:",
            "  default:",
            "    name: naybinho-network",
            "    external: true",
        ])
        return "\n".join(lines)

    def uninstall_app(self, app_id: str) -> Dict[str, Any]:
        """Desinstala o app e remove os contêineres."""
        installed = _load_installed()
        if app_id not in installed:
            clean_id = re.sub(r"[^a-zA-Z0-9_-]", "-", app_id)
            if clean_id in installed:
                app_id = clean_id
            else:
                raise ValueError(f"App '{app_id}' não está instalado.")

        entry = installed[app_id]
        app_dir = Path(entry.get("app_dir", str(APPS_DIR / app_id)))
        compose_file = app_dir / "docker-compose.yml"

        if compose_file.exists():
            subprocess.run(
                ["docker", "compose", "-f", str(compose_file), "down", "--volumes"],
                capture_output=True,
                text=True,
                cwd=str(app_dir),
            )

        try:
            if app_dir.exists():
                shutil.rmtree(str(app_dir), ignore_errors=True)
        except Exception:
            pass

        del installed[app_id]
        _save_installed(installed)
        return {"app_id": app_id, "success": True}

    def list_installed(self) -> List[Dict[str, Any]]:
        """Retorna lista de aplicativos instalados."""
        return list(_load_installed().values())


# Singleton
_apps_service: Optional[AppsService] = None


def get_apps_service() -> AppsService:
    global _apps_service
    if _apps_service is None:
        _apps_service = AppsService()
    return _apps_service
