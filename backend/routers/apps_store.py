"""
NayBinho NAS — App Store Router (Multi-Store / Multi-Repository).

Endpoints:
  GET    /api/store/sources              — List all configured app stores/sources
  POST   /api/store/sources              — Add a new store/source URL
  PUT    /api/store/sources/{source_id}  — Update source (toggle enabled/name)
  DELETE /api/store/sources/{source_id}  — Remove a custom store
  POST   /api/store/sources/sync         — Sync all active stores in background
  POST   /api/store/sources/{source_id}/sync — Sync specific store
  GET    /api/store/apps                 — List all available apps (filters: category, search, source)
  POST   /api/store/apps/{id}/install    — Install an app from catalog
  DELETE /api/store/apps/{id}/uninstall  — Uninstall an app
  GET    /api/store/apps/installed       — List currently installed apps
  GET    /api/store/categories           — List unique categories
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

from middleware.auth import decode_token
from services.apps_service import get_apps_service

router = APIRouter(prefix="/store", tags=["App Store"])
security = HTTPBearer()


def _require_admin(credentials: HTTPAuthorizationCredentials = Depends(security)):
    payload = decode_token(credentials.credentials)
    if payload.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
    return payload


def _require_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    return decode_token(credentials.credentials)


class AddSourceRequest(BaseModel):
    name: str = Field(..., description="Nome da loja/fonte", min_length=2)
    url: str = Field(..., description="URL completa para o arquivo store.json")
    description: Optional[str] = Field(default="", description="Descrição da loja")
    type: Optional[str] = Field(default="casaos", description="Tipo de repositório (casaos/zima/native)")
    icon: Optional[str] = Field(default="📦", description="Emoji ou URL de ícone")


class UpdateSourceRequest(BaseModel):
    name: Optional[str] = None
    enabled: Optional[bool] = None


# ─────────────────────────────────────────────────────────────────────────────
# GESTÃO DE FONTES / LOJAS (MULTI-STORE)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/sources")
async def list_sources():
    """Retorna todas as lojas/fontes configuradas com contadores e status de sincronização."""
    svc = get_apps_service()
    return svc.get_sources()


@router.post("/sources", status_code=201)
async def add_source(
    body: AddSourceRequest,
    background_tasks: BackgroundTasks,
    _: dict = Depends(_require_admin),
):
    """Adiciona uma nova loja (URL de store.json) e dispara a sincronização inicial."""
    svc = get_apps_service()
    try:
        source = svc.add_source(
            name=body.name,
            url=body.url,
            description=body.description or "",
            store_type=body.type or "casaos",
            icon=body.icon or "📦",
        )
        # Sincroniza em background
        background_tasks.add_task(svc.sync_source, source["id"])
        return {"message": f"Loja '{body.name}' adicionada com sucesso.", "source": source}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Falha ao registrar fonte: {e}")


@router.put("/sources/{source_id}")
async def update_source(
    source_id: str,
    body: UpdateSourceRequest,
    _: dict = Depends(_require_admin),
):
    """Ativa/desativa ou altera uma loja."""
    svc = get_apps_service()
    try:
        updated = svc.update_source(source_id=source_id, enabled=body.enabled, name=body.name)
        return {"message": "Fonte atualizada.", "source": updated}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/sources/{source_id}")
async def delete_source(
    source_id: str,
    _: dict = Depends(_require_admin),
):
    """Remove uma loja customizada."""
    svc = get_apps_service()
    try:
        success = svc.remove_source(source_id)
        if not success:
            raise HTTPException(status_code=404, detail="Fonte não encontrada.")
        return {"message": f"Fonte '{source_id}' removida com sucesso."}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sources/sync")
async def sync_all_sources(
    background_tasks: BackgroundTasks,
    _: dict = Depends(_require_admin),
):
    """Dispara a sincronização de todas as lojas ativas."""
    svc = get_apps_service()
    background_tasks.add_task(svc.sync_all_sources)
    return {"message": "Sincronização de todas as lojas iniciada em segundo plano."}


@router.post("/sources/{source_id}/sync")
async def sync_single_source(
    source_id: str,
    background_tasks: BackgroundTasks,
    _: dict = Depends(_require_admin),
):
    """Dispara a sincronização de uma loja específica."""
    svc = get_apps_service()
    background_tasks.add_task(svc.sync_source, source_id)
    return {"message": f"Sincronização da loja '{source_id}' iniciada."}


# ─────────────────────────────────────────────────────────────────────────────
# CATÁLOGO DE APLICATIVOS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/apps")
async def list_store_apps(
    category: Optional[str] = None,
    search: Optional[str] = None,
    source: Optional[str] = Query(None, alias="source_id"),
):
    """Lista aplicativos agregados de todas as lojas ativas ou de uma fonte específica."""
    svc = get_apps_service()
    apps = svc.search_apps(query=search or "", category=category or "", source_id=source)
    return apps


@router.get("/categories")
async def list_categories():
    """Retorna lista de categorias disponíveis no catálogo agregado."""
    svc = get_apps_service()
    catalog = svc.get_catalog()
    cats = sorted({a.get("category", "General") for a in catalog if a.get("category")})
    return ["Todos"] + [c for c in cats if c != "Todos"]


@router.get("/apps/installed")
async def list_installed_apps(_: dict = Depends(_require_user)):
    """Lista aplicativos atualmente instalados."""
    svc = get_apps_service()
    return svc.list_installed()


@router.post("/apps/{app_id}/install", status_code=202)
async def install_app(
    app_id: str,
    background_tasks: BackgroundTasks,
    _: dict = Depends(_require_admin),
):
    """Instala um aplicativo a partir de qualquer uma das lojas ativas."""
    svc = get_apps_service()
    app = svc.get_app_by_id(app_id)
    if not app:
        raise HTTPException(status_code=404, detail=f"Aplicativo '{app_id}' não encontrado em nenhuma loja.")

    background_tasks.add_task(svc.install_app, app_id)
    return {"message": f"Instalação iniciada para {app.get('name', app_id)}", "app_id": app_id}


@router.delete("/apps/{app_id}/uninstall")
async def uninstall_app(
    app_id: str,
    background_tasks: BackgroundTasks,
    _: dict = Depends(_require_admin),
):
    """Desinstala um aplicativo."""
    svc = get_apps_service()
    background_tasks.add_task(svc.uninstall_app, app_id)
    return {"message": f"Desinstalação do aplicativo '{app_id}' iniciada."}
