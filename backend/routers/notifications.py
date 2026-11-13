import datetime
import uuid
import smtplib
from email.mime.text import MIMEText
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, status
import urllib.request
import json

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

# --- Models Pydantic ---

class NotificationItem(BaseModel):
    id: str
    title: str
    message: str
    severity: str = Field("info", description="info, warning, error, critical")
    timestamp: str
    read: bool = False
    source: str = "system"


class NotificationSettings(BaseModel):
    email_enabled: bool = False
    email_smtp_host: str = ""
    email_smtp_port: int = 587
    email_username: str = ""
    email_password: str = ""
    email_from: str = ""
    email_to: str = ""
    email_use_tls: bool = True

    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    discord_enabled: bool = False
    discord_webhook_url: str = ""

    slack_enabled: bool = False
    slack_webhook_url: str = ""

    pushover_enabled: bool = False
    pushover_user_key: str = ""
    pushover_api_token: str = ""

    notify_on_smart_failure: bool = True
    notify_on_raid_degrade: bool = True
    notify_on_high_temperature: bool = True
    notify_on_disk_full: bool = True


class NotificationTestRequest(BaseModel):
    channel: str = Field(..., description="email, telegram, discord, slack, pushover")
    settings: Optional[NotificationSettings] = None


# --- Armazenamento em Memória / Estado Padrão ---

_notifications_db: List[dict] = [
    {
        "id": "notif-001",
        "title": "Sistema Iniciado",
        "message": "NayBinho NAS inicializou todos os serviços com sucesso.",
        "severity": "info",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "read": False,
        "source": "system"
    },
    {
        "id": "notif-002",
        "title": "Atualização Disponível",
        "message": "Pacotes de segurança do Ubuntu 26.04.1 LTS prontos para instalação.",
        "severity": "warning",
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "read": False,
        "source": "updater"
    }
]

_settings_db: NotificationSettings = NotificationSettings()


# --- Rotas da API ---

@router.get("", response_model=List[NotificationItem])
async def list_notifications(unread_only: bool = False):
    """Lista as notificações registradas no sistema."""
    if unread_only:
        return [n for n in _notifications_db if not n["read"]]
    return _notifications_db


@router.post("/{notification_id}/read")
async def mark_as_read(notification_id: str):
    """Marca uma notificação específica como lida."""
    for notif in _notifications_db:
        if notif["id"] == notification_id:
            notif["read"] = True
            return {"success": True, "message": "Notificação marcada como lida."}
    raise HTTPException(status_code=404, detail="Notificação não encontrada.")


@router.post("/read-all")
async def mark_all_as_read():
    """Marca todas as notificações existentes como lidas."""
    for notif in _notifications_db:
        notif["read"] = True
    return {"success": True, "message": "Todas as notificações foram marcadas como lidas."}


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(notification_id: str):
    """Exclui uma notificação pelo seu ID."""
    global _notifications_db
    initial_count = len(_notifications_db)
    _notifications_db = [n for n in _notifications_db if n["id"] != notification_id]
    if len(_notifications_db) == initial_count:
        raise HTTPException(status_code=404, detail="Notificação não encontrada.")
    return None


@router.get("/settings", response_model=NotificationSettings)
async def get_notification_settings():
    """Obtém as credenciais e configurações ativas de todos os canais de notificação."""
    return _settings_db


@router.put("/settings", response_model=NotificationSettings)
async def update_notification_settings(new_settings: NotificationSettings):
    """Atualiza as configurações de canais e alertas de notificação."""
    global _settings_db
    _settings_db = new_settings
    return _settings_db


@router.post("/test")
async def test_notification_channel(req: NotificationTestRequest):
    """Dispara uma mensagem de teste para o canal especificado (email, telegram, discord, slack ou pushover)."""
    cfg = req.settings or _settings_db
    ch = req.channel.lower()
    test_title = "🔔 Teste de Notificação — NayBinho NAS"
    test_message = f"Este é um teste bem-sucedido de notificação do seu NayBinho NAS enviado às {datetime.datetime.now().strftime('%H:%M:%S')}."

    if ch == "discord":
        url = cfg.discord_webhook_url
        if not url:
            raise HTTPException(status_code=400, detail="URL de webhook do Discord não informada.")
        payload = json.dumps({"content": f"**{test_title}**\n{test_message}"}).encode("utf-8")
        req_obj = urllib.request.Request(url, data=payload, headers={"User-Agent": "NayBinho-NAS", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req_obj, timeout=5) as resp:
                if resp.status not in (200, 204):
                    raise Exception(f"Status HTTP {resp.status}")
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Falha ao enviar webhook Discord: {str(err)}")

    elif ch == "telegram":
        token = cfg.telegram_bot_token
        chat_id = cfg.telegram_chat_id
        if not token or not chat_id:
            raise HTTPException(status_code=400, detail="Bot Token ou Chat ID do Telegram não informados.")
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = json.dumps({"chat_id": chat_id, "text": f"{test_title}\n\n{test_message}", "parse_mode": "Markdown"}).encode("utf-8")
        req_obj = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req_obj, timeout=5) as resp:
                if resp.status != 200:
                    raise Exception(f"Status HTTP {resp.status}")
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Falha ao enviar mensagem Telegram: {str(err)}")

    elif ch == "email":
        if not cfg.email_smtp_host or not cfg.email_to:
            raise HTTPException(status_code=400, detail="Servidor SMTP ou email de destino não configurados.")
        try:
            msg = MIMEText(test_message)
            msg['Subject'] = test_title
            msg['From'] = cfg.email_from or "nas@naybinho.local"
            msg['To'] = cfg.email_to

            with smtplib.SMTP(cfg.email_smtp_host, cfg.email_smtp_port, timeout=5) as server:
                if cfg.email_use_tls:
                    server.starttls()
                if cfg.email_username and cfg.email_password:
                    server.login(cfg.email_username, cfg.email_password)
                server.send_message(msg)
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Falha ao enviar email SMTP: {str(err)}")

    elif ch == "slack":
        url = cfg.slack_webhook_url
        if not url:
            raise HTTPException(status_code=400, detail="URL de webhook do Slack não informada.")
        payload = json.dumps({"text": f"*{test_title}*\n{test_message}"}).encode("utf-8")
        req_obj = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req_obj, timeout=5) as resp:
                if resp.status != 200:
                    raise Exception(f"Status HTTP {resp.status}")
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Falha ao enviar Slack: {str(err)}")

    elif ch == "pushover":
        if not cfg.pushover_user_key or not cfg.pushover_api_token:
            raise HTTPException(status_code=400, detail="User Key ou API Token do Pushover não configurados.")
        url = "https://api.pushover.net/1/messages.json"
        data = urllib.parse.urlencode({
            "token": cfg.pushover_api_token,
            "user": cfg.pushover_user_key,
            "title": test_title,
            "message": test_message,
        }).encode("utf-8")
        req_obj = urllib.request.Request(url, data=data)
        try:
            with urllib.request.urlopen(req_obj, timeout=5) as resp:
                if resp.status != 200:
                    raise Exception(f"Status HTTP {resp.status}")
        except Exception as err:
            raise HTTPException(status_code=500, detail=f"Falha ao enviar Pushover: {str(err)}")

    else:
        raise HTTPException(status_code=400, detail=f"Canal '{req.channel}' não é suportado.")

    return {"success": True, "channel": ch, "message": f"Mensagem de teste enviada com sucesso para o canal {ch}."}
