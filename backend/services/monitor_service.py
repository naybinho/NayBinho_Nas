"""
NayBinho NAS — Monitor Service
Coleta periódica de métricas, alertas e notificações em tempo real.
"""

import asyncio
import json
import logging
import smtplib
import sqlite3
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional, Set

import httpx
import psutil
from fastapi import WebSocket

logger = logging.getLogger("naybinho.monitor")

# ---------------------------------------------------------------------------
# Configuration defaults (overridden via DB settings table)
# ---------------------------------------------------------------------------
DEFAULT_THRESHOLDS = {
    "cpu_percent": 90.0,
    "ram_percent": 90.0,
    "disk_percent": 85.0,
    "temperature_celsius": 70.0,
    "collect_interval_seconds": 10,
    "retention_days": 30,
}

DEFAULT_NOTIFICATIONS = {
    "email_enabled": False,
    "email_smtp_host": "smtp.gmail.com",
    "email_smtp_port": 587,
    "email_smtp_user": "",
    "email_smtp_password": "",
    "email_to": "",
    "webhook_enabled": False,
    "webhook_url": "",
    "telegram_enabled": False,
    "telegram_bot_token": "",
    "telegram_chat_id": "",
}

DB_PATH = Path("/opt/naybinho/data/naybinho.db")


# ---------------------------------------------------------------------------
# In-memory broadcast registry (WebSocket + SSE)
# ---------------------------------------------------------------------------
class ConnectionManager:
    def __init__(self):
        self.ws_clients: Set[WebSocket] = set()
        self.sse_queues: List[asyncio.Queue] = []

    async def connect_ws(self, websocket: WebSocket):
        await websocket.accept()
        self.ws_clients.add(websocket)

    def disconnect_ws(self, websocket: WebSocket):
        self.ws_clients.discard(websocket)

    def add_sse_queue(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=50)
        self.sse_queues.append(q)
        return q

    def remove_sse_queue(self, q: asyncio.Queue):
        try:
            self.sse_queues.remove(q)
        except ValueError:
            pass

    async def broadcast(self, data: dict):
        message = json.dumps(data)
        dead: Set[WebSocket] = set()
        for ws in list(self.ws_clients):
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        self.ws_clients -= dead

        for q in list(self.sse_queues):
            try:
                q.put_nowait(data)
            except asyncio.QueueFull:
                pass


manager = ConnectionManager()


# ---------------------------------------------------------------------------
# Metrics collection
# ---------------------------------------------------------------------------
def _collect_cpu() -> dict:
    return {
        "percent": psutil.cpu_percent(interval=1),
        "count_physical": psutil.cpu_count(logical=False),
        "count_logical": psutil.cpu_count(logical=True),
        "freq_mhz": getattr(psutil.cpu_freq(), "current", 0),
        "load_avg_1m": psutil.getloadavg()[0] if hasattr(psutil, "getloadavg") else 0,
    }


def _collect_ram() -> dict:
    vm = psutil.virtual_memory()
    swap = psutil.swap_memory()
    return {
        "total_gb": round(vm.total / 1024**3, 2),
        "available_gb": round(vm.available / 1024**3, 2),
        "used_gb": round(vm.used / 1024**3, 2),
        "percent": vm.percent,
        "swap_total_gb": round(swap.total / 1024**3, 2),
        "swap_used_gb": round(swap.used / 1024**3, 2),
        "swap_percent": swap.percent,
    }


def _collect_disks() -> list:
    result = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            result.append(
                {
                    "device": part.device,
                    "mountpoint": part.mountpoint,
                    "fstype": part.fstype,
                    "total_gb": round(usage.total / 1024**3, 2),
                    "used_gb": round(usage.used / 1024**3, 2),
                    "free_gb": round(usage.free / 1024**3, 2),
                    "percent": usage.percent,
                }
            )
        except PermissionError:
            continue
    return result


def _collect_network() -> dict:
    counters = psutil.net_io_counters()
    return {
        "bytes_sent": counters.bytes_sent,
        "bytes_recv": counters.bytes_recv,
        "packets_sent": counters.packets_sent,
        "packets_recv": counters.packets_recv,
        "errin": counters.errin,
        "errout": counters.errout,
    }


def _collect_temperatures() -> list:
    result = []
    if not hasattr(psutil, "sensors_temperatures"):
        return result
    try:
        temps = psutil.sensors_temperatures()
        for name, entries in (temps or {}).items():
            for entry in entries:
                result.append(
                    {
                        "sensor": name,
                        "label": entry.label or name,
                        "current": entry.current,
                        "high": entry.high,
                        "critical": entry.critical,
                    }
                )
    except Exception as exc:
        logger.debug("Temperature read failed: %s", exc)
    return result


def _collect_raid_status() -> list:
    """Read /proc/mdstat if available."""
    result = []
    mdstat = Path("/proc/mdstat")
    if not mdstat.exists():
        return result
    try:
        content = mdstat.read_text()
        lines = content.splitlines()
        current = None
        for line in lines:
            if line.startswith("md"):
                parts = line.split()
                current = {
                    "device": parts[0],
                    "status": parts[2] if len(parts) > 2 else "unknown",
                    "level": parts[3] if len(parts) > 3 else "unknown",
                    "degraded": "U" in line and "_" in line,
                    "raw": line,
                }
                result.append(current)
            elif current and line.strip().startswith("["):
                current["progress"] = line.strip()
    except Exception as exc:
        logger.warning("mdstat read failed: %s", exc)
    return result


def collect_all_metrics() -> dict:
    ts = datetime.utcnow().isoformat()
    return {
        "timestamp": ts,
        "cpu": _collect_cpu(),
        "ram": _collect_ram(),
        "disks": _collect_disks(),
        "network": _collect_network(),
        "temperatures": _collect_temperatures(),
        "raid": _collect_raid_status(),
    }


# ---------------------------------------------------------------------------
# Alert generation
# ---------------------------------------------------------------------------
class AlertSeverity:
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


def check_thresholds(metrics: dict, thresholds: dict) -> List[dict]:
    alerts = []
    now = datetime.utcnow().isoformat()

    # CPU
    cpu_pct = metrics["cpu"]["percent"]
    if cpu_pct >= thresholds["cpu_percent"]:
        severity = AlertSeverity.CRITICAL if cpu_pct >= 95 else AlertSeverity.WARNING
        alerts.append(
            {
                "type": "cpu_high",
                "severity": severity,
                "message": f"CPU usage critical: {cpu_pct:.1f}%",
                "value": cpu_pct,
                "threshold": thresholds["cpu_percent"],
                "created_at": now,
            }
        )

    # RAM
    ram_pct = metrics["ram"]["percent"]
    if ram_pct >= thresholds["ram_percent"]:
        severity = AlertSeverity.CRITICAL if ram_pct >= 95 else AlertSeverity.WARNING
        alerts.append(
            {
                "type": "ram_high",
                "severity": severity,
                "message": f"RAM usage critical: {ram_pct:.1f}%",
                "value": ram_pct,
                "threshold": thresholds["ram_percent"],
                "created_at": now,
            }
        )

    # Disks
    for disk in metrics["disks"]:
        if disk["percent"] >= thresholds["disk_percent"]:
            severity = (
                AlertSeverity.CRITICAL if disk["percent"] >= 95 else AlertSeverity.WARNING
            )
            alerts.append(
                {
                    "type": "disk_high",
                    "severity": severity,
                    "message": f"Disk {disk['mountpoint']} usage: {disk['percent']:.1f}%",
                    "value": disk["percent"],
                    "threshold": thresholds["disk_percent"],
                    "device": disk["device"],
                    "created_at": now,
                }
            )

    # Temperatures
    for temp in metrics["temperatures"]:
        if temp["current"] >= thresholds["temperature_celsius"]:
            severity = (
                AlertSeverity.CRITICAL
                if temp["current"] >= 85
                else AlertSeverity.WARNING
            )
            alerts.append(
                {
                    "type": "temperature_high",
                    "severity": severity,
                    "message": f"Temperature {temp['label']}: {temp['current']}°C",
                    "value": temp["current"],
                    "threshold": thresholds["temperature_celsius"],
                    "sensor": temp["sensor"],
                    "created_at": now,
                }
            )

    # RAID
    for raid in metrics.get("raid", []):
        if raid.get("degraded"):
            alerts.append(
                {
                    "type": "raid_degraded",
                    "severity": AlertSeverity.CRITICAL,
                    "message": f"RAID array {raid['device']} is DEGRADED",
                    "value": None,
                    "threshold": None,
                    "device": raid["device"],
                    "created_at": now,
                }
            )

    return alerts


# ---------------------------------------------------------------------------
# Notification dispatchers
# ---------------------------------------------------------------------------
async def _send_email(settings: dict, subject: str, body: str):
    try:
        msg = MIMEMultipart()
        msg["From"] = settings["email_smtp_user"]
        msg["To"] = settings["email_to"]
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(settings["email_smtp_host"], settings["email_smtp_port"]) as srv:
            srv.starttls()
            srv.login(settings["email_smtp_user"], settings["email_smtp_password"])
            srv.send_message(msg)
        logger.info("Alert email sent to %s", settings["email_to"])
    except Exception as exc:
        logger.error("Email send failed: %s", exc)


async def _send_webhook(url: str, payload: dict):
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
        logger.info("Webhook delivered to %s", url)
    except Exception as exc:
        logger.error("Webhook failed: %s", exc)


async def _send_telegram(bot_token: str, chat_id: str, text: str):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"})
            resp.raise_for_status()
        logger.info("Telegram message sent to chat %s", chat_id)
    except Exception as exc:
        logger.error("Telegram send failed: %s", exc)


async def dispatch_notifications(alert: dict, notif_settings: dict):
    subject = f"[NayBinho NAS] {alert['severity'].upper()} — {alert['message']}"
    body = (
        f"Alert: {alert['message']}\n"
        f"Severity: {alert['severity']}\n"
        f"Type: {alert['type']}\n"
        f"Time: {alert['created_at']}\n"
        f"Value: {alert.get('value', 'N/A')}\n"
        f"Threshold: {alert.get('threshold', 'N/A')}\n"
    )

    tasks = []
    if notif_settings.get("email_enabled"):
        tasks.append(_send_email(notif_settings, subject, body))
    if notif_settings.get("webhook_enabled") and notif_settings.get("webhook_url"):
        tasks.append(_send_webhook(notif_settings["webhook_url"], alert))
    if notif_settings.get("telegram_enabled"):
        tg_text = f"🚨 <b>{alert['severity'].upper()}</b>\n{alert['message']}\nTime: {alert['created_at']}"
        tasks.append(
            _send_telegram(
                notif_settings["telegram_bot_token"],
                notif_settings["telegram_chat_id"],
                tg_text,
            )
        )
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


# ---------------------------------------------------------------------------
# SQLite persistence helpers
# ---------------------------------------------------------------------------
def _get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_tables():
    with _get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS metrics_history (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp  TEXT NOT NULL,
                cpu_pct    REAL,
                ram_pct    REAL,
                net_sent   INTEGER,
                net_recv   INTEGER,
                payload    TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_mh_ts ON metrics_history(timestamp);

            CREATE TABLE IF NOT EXISTS alerts (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                type         TEXT NOT NULL,
                severity     TEXT NOT NULL,
                message      TEXT NOT NULL,
                value        REAL,
                threshold    REAL,
                extra        TEXT,
                created_at   TEXT NOT NULL,
                dismissed    INTEGER DEFAULT 0,
                dismissed_at TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_al_created ON alerts(created_at);

            CREATE TABLE IF NOT EXISTS settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )


def _save_metrics(metrics: dict):
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO metrics_history (timestamp, cpu_pct, ram_pct, net_sent, net_recv, payload) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                metrics["timestamp"],
                metrics["cpu"]["percent"],
                metrics["ram"]["percent"],
                metrics["network"]["bytes_sent"],
                metrics["network"]["bytes_recv"],
                json.dumps(metrics),
            ),
        )


def _save_alert(alert: dict):
    extra = json.dumps({k: v for k, v in alert.items() if k not in ("type", "severity", "message", "value", "threshold", "created_at")})
    with _get_conn() as conn:
        conn.execute(
            "INSERT INTO alerts (type, severity, message, value, threshold, extra, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                alert["type"],
                alert["severity"],
                alert["message"],
                alert.get("value"),
                alert.get("threshold"),
                extra,
                alert["created_at"],
            ),
        )


def _purge_old_metrics(retention_days: int):
    cutoff = (datetime.utcnow() - timedelta(days=retention_days)).isoformat()
    with _get_conn() as conn:
        conn.execute("DELETE FROM metrics_history WHERE timestamp < ?", (cutoff,))


def _load_settings() -> dict:
    thresholds = dict(DEFAULT_THRESHOLDS)
    notifications = dict(DEFAULT_NOTIFICATIONS)
    try:
        with _get_conn() as conn:
            for row in conn.execute("SELECT key, value FROM settings"):
                k, v = row["key"], row["value"]
                try:
                    parsed = json.loads(v)
                except Exception:
                    parsed = v
                if k in thresholds:
                    thresholds[k] = parsed
                elif k in notifications:
                    notifications[k] = parsed
    except Exception:
        pass
    return {"thresholds": thresholds, "notifications": notifications}


# ---------------------------------------------------------------------------
# Deduplication: only alert once per active period
# ---------------------------------------------------------------------------
_active_alert_types: Set[str] = set()


def _is_new_alert(alert_type: str) -> bool:
    if alert_type in _active_alert_types:
        return False
    _active_alert_types.add(alert_type)
    return True


def _clear_resolved(current_alert_types: Set[str]):
    resolved = _active_alert_types - current_alert_types
    _active_alert_types -= resolved


# ---------------------------------------------------------------------------
# Background collection loop
# ---------------------------------------------------------------------------
async def _collection_loop():
    _ensure_tables()
    logger.info("Monitor collection loop started")
    tick = 0
    while True:
        try:
            cfg = _load_settings()
            thresholds = cfg["thresholds"]
            notifications = cfg["notifications"]
            interval = int(thresholds.get("collect_interval_seconds", 10))
            retention = int(thresholds.get("retention_days", 30))

            metrics = collect_all_metrics()
            _save_metrics(metrics)

            # Purge old data every 100 ticks
            if tick % 100 == 0:
                _purge_old_metrics(retention)
            tick += 1

            # Check thresholds → alerts
            new_alerts = check_thresholds(metrics, thresholds)
            current_types = {a["type"] for a in new_alerts}
            _clear_resolved(current_types)

            for alert in new_alerts:
                if _is_new_alert(alert["type"]):
                    _save_alert(alert)
                    await dispatch_notifications(alert, notifications)
                    # Broadcast alert over WS/SSE
                    await manager.broadcast({"event": "alert", "data": alert})

            # Broadcast live metrics
            await manager.broadcast({"event": "metrics", "data": metrics})

        except asyncio.CancelledError:
            logger.info("Monitor collection loop cancelled")
            break
        except Exception as exc:
            logger.exception("Error in collection loop: %s", exc)

        await asyncio.sleep(interval)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
_loop_task: Optional[asyncio.Task] = None


def start_monitor():
    global _loop_task
    if _loop_task is None or _loop_task.done():
        _loop_task = asyncio.create_task(_collection_loop())
        logger.info("Monitor task started")


def stop_monitor():
    global _loop_task
    if _loop_task and not _loop_task.done():
        _loop_task.cancel()
        logger.info("Monitor task stopped")


def get_metrics_history(period: str = "1h") -> List[dict]:
    """Return metrics history for the given period."""
    period_map = {"1h": 1, "6h": 6, "24h": 24, "7d": 168}
    hours = period_map.get(period, 1)
    cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    with _get_conn() as conn:
        rows = conn.execute(
            "SELECT timestamp, cpu_pct, ram_pct, net_sent, net_recv, payload "
            "FROM metrics_history WHERE timestamp >= ? ORDER BY timestamp ASC",
            (cutoff,),
        ).fetchall()
    result = []
    for row in rows:
        try:
            payload = json.loads(row["payload"])
        except Exception:
            payload = {}
        result.append(
            {
                "timestamp": row["timestamp"],
                "cpu_pct": row["cpu_pct"],
                "ram_pct": row["ram_pct"],
                "net_sent": row["net_sent"],
                "net_recv": row["net_recv"],
                **payload,
            }
        )
    return result


def get_alerts(active_only: bool = False) -> List[dict]:
    with _get_conn() as conn:
        query = "SELECT * FROM alerts"
        if active_only:
            query += " WHERE dismissed = 0"
        query += " ORDER BY created_at DESC LIMIT 500"
        rows = conn.execute(query).fetchall()
    return [dict(r) for r in rows]


def dismiss_alert(alert_id: int) -> bool:
    now = datetime.utcnow().isoformat()
    with _get_conn() as conn:
        cur = conn.execute(
            "UPDATE alerts SET dismissed=1, dismissed_at=? WHERE id=?",
            (now, alert_id),
        )
        return cur.rowcount > 0


def get_settings() -> dict:
    return _load_settings()


def update_settings(new_settings: dict) -> dict:
    with _get_conn() as conn:
        for k, v in new_settings.items():
            conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (k, json.dumps(v)),
            )
    return _load_settings()


async def websocket_handler(websocket: WebSocket):
    await manager.connect_ws(websocket)
    try:
        # Send current metrics immediately on connect
        try:
            current = collect_all_metrics()
            await websocket.send_text(json.dumps({"event": "metrics", "data": current}))
        except Exception:
            pass
        # Keep alive — just wait for disconnect
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                await websocket.send_text(json.dumps({"event": "ping"}))
    except Exception:
        pass
    finally:
        manager.disconnect_ws(websocket)


async def sse_generator() -> AsyncGenerator[str, None]:
    q = manager.add_sse_queue()
    try:
        # Send current state immediately
        current = collect_all_metrics()
        yield f"data: {json.dumps({'event': 'metrics', 'data': current})}\n\n"
        while True:
            try:
                data = await asyncio.wait_for(q.get(), timeout=30)
                yield f"data: {json.dumps(data)}\n\n"
            except asyncio.TimeoutError:
                yield ": keepalive\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        manager.remove_sse_queue(q)
