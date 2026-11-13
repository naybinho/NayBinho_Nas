"""
NayBinho NAS — Log Service
Leitura, parsing, busca e exportação de logs do sistema.
"""

import gzip
import io
import json
import logging
import os
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterator, List, Optional

logger = logging.getLogger("naybinho.logs")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
NAYBINHO_LOG_DIR = Path("/opt/naybinho/logs")
NAYBINHO_LOG_FILE = NAYBINHO_LOG_DIR / "naybinho.log"
MAX_LOG_SIZE_MB = 50
MAX_ROTATED_FILES = 7

LOG_LEVELS = {"debug", "info", "warning", "error", "critical"}

SYSLOG_PATHS = [
    Path("/var/log/syslog"),
    Path("/var/log/messages"),
]

# ---------------------------------------------------------------------------
# NayBinho structured logger
# ---------------------------------------------------------------------------
def _get_app_logger() -> logging.Logger:
    """Return a configured logger that writes to the NayBinho log file."""
    NAYBINHO_LOG_DIR.mkdir(parents=True, exist_ok=True)
    app_logger = logging.getLogger("naybinho.app")
    if app_logger.handlers:
        return app_logger
    app_logger.setLevel(logging.DEBUG)
    handler = logging.FileHandler(str(NAYBINHO_LOG_FILE))
    handler.setFormatter(
        logging.Formatter(
            fmt='{"time":"%(asctime)s","level":"%(levelname)s","module":"%(name)s","msg":%(message)s}',
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    app_logger.addHandler(handler)
    return app_logger


app_logger = _get_app_logger()


def log_action(action: str, user: str = "system", detail: dict = None):
    """Log a NayBinho user/system action in structured format."""
    payload = json.dumps(
        {"action": action, "user": user, "detail": detail or {}}
    )
    app_logger.info(payload)


def log_error(source: str, message: str, detail: dict = None):
    payload = json.dumps({"source": source, "message": message, "detail": detail or {}})
    app_logger.error(payload)


def log_install(app_id: str, version: str, user: str, success: bool, detail: str = ""):
    payload = json.dumps(
        {
            "action": "app_install",
            "app_id": app_id,
            "version": version,
            "user": user,
            "success": success,
            "detail": detail,
        }
    )
    if success:
        app_logger.info(payload)
    else:
        app_logger.error(payload)


# ---------------------------------------------------------------------------
# Log rotation
# ---------------------------------------------------------------------------
def rotate_naybinho_log():
    """Manual rotation: compress current log and start fresh."""
    if not NAYBINHO_LOG_FILE.exists():
        return
    size_mb = NAYBINHO_LOG_FILE.stat().st_size / (1024 * 1024)
    if size_mb < MAX_LOG_SIZE_MB:
        return

    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    rotated_name = NAYBINHO_LOG_DIR / f"naybinho.{ts}.log.gz"
    with NAYBINHO_LOG_FILE.open("rb") as f_in, gzip.open(str(rotated_name), "wb") as f_out:
        f_out.writelines(f_in)
    NAYBINHO_LOG_FILE.unlink()
    NAYBINHO_LOG_FILE.touch()

    # Prune old rotated files
    rotated = sorted(NAYBINHO_LOG_DIR.glob("naybinho.*.log.gz"))
    while len(rotated) > MAX_ROTATED_FILES:
        rotated.pop(0).unlink()

    logger.info("Log rotated to %s", rotated_name)


# ---------------------------------------------------------------------------
# Journald reader
# ---------------------------------------------------------------------------
def _read_journald(
    service: Optional[str],
    since: Optional[str],
    until: Optional[str],
    limit: int,
) -> List[dict]:
    """Query journald via journalctl --output=json."""
    cmd = ["journalctl", "--output=json", f"-n{limit}", "--no-pager"]
    if service and service != "all":
        cmd += ["-u", service]
    if since:
        cmd += ["--since", since]
    if until:
        cmd += ["--until", until]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        entries = []
        for line in result.stdout.splitlines():
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                entries.append(
                    {
                        "source": "journald",
                        "timestamp": _journal_ts(raw.get("__REALTIME_TIMESTAMP", "")),
                        "level": _journal_level(raw.get("PRIORITY", "6")),
                        "unit": raw.get("_SYSTEMD_UNIT", ""),
                        "message": raw.get("MESSAGE", ""),
                        "pid": raw.get("_PID", ""),
                        "hostname": raw.get("_HOSTNAME", ""),
                    }
                )
            except json.JSONDecodeError:
                continue
        return entries
    except FileNotFoundError:
        logger.debug("journalctl not available")
        return []
    except subprocess.TimeoutExpired:
        logger.warning("journalctl query timed out")
        return []


def _journal_ts(raw_ts: str) -> str:
    if not raw_ts:
        return ""
    try:
        ts_us = int(raw_ts)
        return datetime.utcfromtimestamp(ts_us / 1_000_000).isoformat()
    except Exception:
        return raw_ts


def _journal_level(priority: str) -> str:
    mapping = {
        "0": "critical",
        "1": "critical",
        "2": "critical",
        "3": "error",
        "4": "warning",
        "5": "info",
        "6": "info",
        "7": "debug",
    }
    return mapping.get(str(priority), "info")


# ---------------------------------------------------------------------------
# Syslog reader (fallback)
# ---------------------------------------------------------------------------
_SYSLOG_RE = re.compile(
    r"^(?P<month>\w+)\s+(?P<day>\d+)\s+(?P<time>\d{2}:\d{2}:\d{2})\s+"
    r"(?P<host>\S+)\s+(?P<process>[^:]+):\s+(?P<message>.*)$"
)


def _read_syslog(limit: int, level_filter: Optional[str]) -> List[dict]:
    for log_path in SYSLOG_PATHS:
        if log_path.exists():
            return _parse_syslog(log_path, limit, level_filter)
    return []


def _parse_syslog(path: Path, limit: int, level_filter: Optional[str]) -> List[dict]:
    result = []
    try:
        with path.open("r", errors="replace") as f:
            lines = f.readlines()
        for line in reversed(lines[-5000:]):
            m = _SYSLOG_RE.match(line.strip())
            if not m:
                continue
            level = _guess_level(m.group("message"))
            if level_filter and level_filter != "all" and level != level_filter:
                continue
            result.append(
                {
                    "source": "syslog",
                    "timestamp": m.group("time"),
                    "level": level,
                    "unit": m.group("process"),
                    "message": m.group("message"),
                    "hostname": m.group("host"),
                }
            )
            if len(result) >= limit:
                break
    except Exception as exc:
        logger.warning("Syslog parse error: %s", exc)
    return result


def _guess_level(message: str) -> str:
    msg_lower = message.lower()
    if any(w in msg_lower for w in ("crit", "emerg", "alert", "panic")):
        return "critical"
    if "error" in msg_lower or "err" in msg_lower:
        return "error"
    if "warn" in msg_lower:
        return "warning"
    if "debug" in msg_lower:
        return "debug"
    return "info"


# ---------------------------------------------------------------------------
# NayBinho app log reader
# ---------------------------------------------------------------------------
def _read_naybinho_logs(limit: int, level_filter: Optional[str], search: Optional[str]) -> List[dict]:
    result = []
    if not NAYBINHO_LOG_FILE.exists():
        return result
    try:
        with NAYBINHO_LOG_FILE.open("r", errors="replace") as f:
            lines = f.readlines()
        for line in reversed(lines[-10000:]):
            line = line.strip()
            if not line:
                continue
            # Try structured JSON parse
            try:
                entry = json.loads(line)
                level = entry.get("level", "info").lower()
                if level_filter and level_filter != "all" and level != level_filter:
                    continue
                msg = json.dumps(entry.get("msg", entry))
                if search and search.lower() not in msg.lower():
                    continue
                result.append(
                    {
                        "source": "naybinho",
                        "timestamp": entry.get("time", ""),
                        "level": level,
                        "unit": entry.get("module", "naybinho"),
                        "message": msg,
                    }
                )
            except json.JSONDecodeError:
                # Plain text fallback
                level = _guess_level(line)
                if level_filter and level_filter != "all" and level != level_filter:
                    continue
                if search and search.lower() not in line.lower():
                    continue
                result.append(
                    {"source": "naybinho", "timestamp": "", "level": level, "unit": "naybinho", "message": line}
                )
            if len(result) >= limit:
                break
    except Exception as exc:
        logger.warning("NayBinho log read error: %s", exc)
    return result


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def get_logs(
    service: str = "all",
    level: str = "all",
    limit: int = 100,
    search: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> List[dict]:
    """
    Return merged log entries from journald, syslog and NayBinho app log.

    Args:
        service: systemd unit name or 'all'
        level:   debug|info|warning|error|critical|all
        limit:   max entries to return
        search:  substring filter on message
        since:   ISO8601 or journald time spec
        until:   ISO8601 or journald time spec
    """
    level = level.lower() if level else "all"
    entries: List[dict] = []

    # journald
    jd_entries = _read_journald(service, since, until, limit * 2)
    for e in jd_entries:
        if level != "all" and e["level"] != level:
            continue
        if search and search.lower() not in e["message"].lower():
            continue
        entries.append(e)

    # naybinho app log
    nay_entries = _read_naybinho_logs(limit * 2, level if level != "all" else None, search)
    entries.extend(nay_entries)

    # syslog fallback if journald returned nothing
    if not jd_entries:
        sl_entries = _read_syslog(limit * 2, level if level != "all" else None)
        for e in sl_entries:
            if search and search.lower() not in e["message"].lower():
                continue
            entries.append(e)

    # Sort by timestamp desc (best effort), truncate
    try:
        entries.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
    except Exception:
        pass

    return entries[:limit]


def search_logs(query: str, limit: int = 200) -> List[dict]:
    """Full-text search across all log sources."""
    return get_logs(search=query, limit=limit)


def export_logs(
    fmt: str = "json",
    service: str = "all",
    level: str = "all",
    since: Optional[str] = None,
    limit: int = 5000,
) -> bytes:
    """
    Export logs as JSON or plain text bytes.

    Args:
        fmt:   'json' or 'text'
        ...
    """
    entries = get_logs(service=service, level=level, limit=limit, since=since)
    if fmt == "json":
        return json.dumps(entries, indent=2).encode()
    # plain text
    lines = []
    for e in entries:
        lines.append(
            f"[{e.get('timestamp','')}] [{e.get('level','').upper():8}] "
            f"[{e.get('unit','')}] {e.get('message','')}"
        )
    return "\n".join(lines).encode()


def get_naybinho_log_files() -> List[dict]:
    """List all NayBinho log files (current + rotated)."""
    result = []
    if not NAYBINHO_LOG_DIR.exists():
        return result
    for f in sorted(NAYBINHO_LOG_DIR.iterdir()):
        stat = f.stat()
        result.append(
            {
                "name": f.name,
                "path": str(f),
                "size_bytes": stat.st_size,
                "modified": datetime.utcfromtimestamp(stat.st_mtime).isoformat(),
                "compressed": f.suffix == ".gz",
            }
        )
    return result


def get_systemd_units() -> List[str]:
    """Return list of active systemd unit names for the service filter dropdown."""
    try:
        result = subprocess.run(
            ["systemctl", "list-units", "--type=service", "--state=active", "--no-pager", "--plain"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        units = []
        for line in result.stdout.splitlines():
            parts = line.split()
            if parts and parts[0].endswith(".service"):
                units.append(parts[0])
        return units
    except Exception:
        return []
