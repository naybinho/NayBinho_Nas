"""
NayBinho NAS — FastAPI Monitoring Router
Endpoints para métricas, alertas, logs, configurações e streaming em tempo real (WS / SSE).
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, status
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field

from backend.services import log_service, monitor_service

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])


# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------
class ThresholdsConfig(BaseModel):
    cpu_percent: float = Field(90.0, ge=1.0, le=100.0)
    ram_percent: float = Field(90.0, ge=1.0, le=100.0)
    disk_percent: float = Field(85.0, ge=1.0, le=100.0)
    temperature_celsius: float = Field(70.0, ge=20.0, le=120.0)
    collect_interval_seconds: int = Field(10, ge=1, le=3600)
    retention_days: int = Field(30, ge=1, le=365)


class NotificationConfig(BaseModel):
    email_enabled: bool = False
    email_smtp_host: str = "smtp.gmail.com"
    email_smtp_port: int = 587
    email_smtp_user: str = ""
    email_smtp_password: str = ""
    email_to: str = ""
    webhook_enabled: bool = False
    webhook_url: str = ""
    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""


class SettingsUpdatePayload(BaseModel):
    thresholds: Optional[ThresholdsConfig] = None
    notifications: Optional[NotificationConfig] = None


class AlertDismissResponse(BaseModel):
    success: bool
    message: str


# ---------------------------------------------------------------------------
# Metrics History
# ---------------------------------------------------------------------------
@router.get("/metrics")
async def get_metrics_history(
    period: str = Query("1h", regex="^(1h|6h|24h|7d)$", description="Histórico de tempo desejado")
):
    """
    Retorna série histórica de métricas consolidadas (CPU, RAM, Disco, Rede, Temperatura).
    """
    data = monitor_service.get_metrics_history(period=period)
    return {"period": period, "count": len(data), "metrics": data}


# ---------------------------------------------------------------------------
# Alerts Endpoints
# ---------------------------------------------------------------------------
@router.get("/alerts")
async def get_alerts(
    active_only: bool = Query(False, description="Filtrar apenas alertas não resolvidos/não dispensados")
):
    """
    Retorna histórico e lista de alertas gerados pelo sistema.
    """
    alerts = monitor_service.get_alerts(active_only=active_only)
    return {"count": len(alerts), "alerts": alerts}


@router.post("/alerts/{alert_id}/dismiss", response_model=AlertDismissResponse)
async def dismiss_alert(alert_id: int):
    """
    Descarta ou reconhece um alerta ativo.
    """
    ok = monitor_service.dismiss_alert(alert_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alerta com ID {alert_id} não encontrado ou já dispensado."
        )
    return AlertDismissResponse(success=True, message=f"Alerta {alert_id} dispensado com sucesso.")


# ---------------------------------------------------------------------------
# Logs Endpoints
# ---------------------------------------------------------------------------
@router.get("/logs")
async def get_logs(
    service: str = Query("all", description="Filtro por unit/serviço systemd ou 'all'"),
    level: str = Query("all", description="debug, info, warning, error, critical ou all"),
    search: Optional[str] = Query(None, description="Termo para busca textual nos logs"),
    limit: int = Query(100, ge=1, le=1000, description="Quantidade máxima de registros"),
    since: Optional[str] = Query(None, description="Filtro de data início (ISO8601)"),
    until: Optional[str] = Query(None, description="Filtro de data fim (ISO8601)"),
):
    """
    Lê e filtra logs do sistema (journald, syslog e logs do aplicativo NayBinho).
    """
    logs = log_service.get_logs(
        service=service,
        level=level,
        limit=limit,
        search=search,
        since=since,
        until=until
    )
    return {"count": len(logs), "logs": logs}


@router.get("/logs/export")
async def export_logs(
    fmt: str = Query("json", regex="^(json|text)$", description="Formato de exportação: json ou text"),
    service: str = Query("all"),
    level: str = Query("all"),
    limit: int = Query(5000, ge=1, le=50000),
):
    """
    Exporta logs para download nos formatos JSON ou texto plano.
    """
    content = log_service.export_logs(fmt=fmt, service=service, level=level, limit=limit)
    media_type = "application/json" if fmt == "json" else "text/plain"
    filename = f"naybinho-logs-{service}.{fmt}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/logs/services")
async def list_log_services():
    """
    Lista serviços systemd ativos para popular filtros na interface.
    """
    services = log_service.get_systemd_units()
    return {"services": services}


# ---------------------------------------------------------------------------
# Settings Endpoints (Thresholds & Notificações)
# ---------------------------------------------------------------------------
@router.get("/settings")
async def get_monitoring_settings():
    """
    Retorna as configurações atuais de monitoramento, limites de alerta e canais de notificação.
    """
    return monitor_service.get_settings()


@router.put("/settings")
async def update_monitoring_settings(payload: SettingsUpdatePayload):
    """
    Atualiza thresholds e preferências de alerta (email, webhook, telegram).
    """
    updates = {}
    if payload.thresholds:
        updates.update(payload.thresholds.dict())
    if payload.notifications:
        updates.update(payload.notifications.dict())

    new_cfg = monitor_service.update_settings(updates)
    return {"message": "Configurações atualizadas com sucesso", "settings": new_cfg}


# ---------------------------------------------------------------------------
# Real-time WebSocket & SSE
# ---------------------------------------------------------------------------
@router.websocket("/ws/stats")
async def websocket_stats_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint dedicado para streaming contínuo de métricas em tempo real (/api/monitoring/ws/stats).
    """
    await monitor_service.websocket_handler(websocket)


# Complementar: rota direta no nível raiz para /ws/stats e /events/stream
# Para permitir que o FastAPI monte nas rotas requeridas na especificação
root_monitoring_router = APIRouter(tags=["monitoring-realtime"])

@root_monitoring_router.websocket("/ws/stats")
async def ws_stats_root(websocket: WebSocket):
    await monitor_service.websocket_handler(websocket)

@root_monitoring_router.get("/events/stream")
async def sse_events_root():
    return StreamingResponse(
        monitor_service.sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
