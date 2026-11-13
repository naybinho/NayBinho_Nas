"""
NayBinho NAS — SMART Monitoring Service
Collects SMART telemetry, parses critical drive health attributes,
manages short/long self-tests, and computes overall health status.
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from backend.models.storage_models import (
    OperationResult,
    SmartAttribute,
    SmartHealth,
    SmartReport,
    SmartTest,
    SmartTestStatus,
    SmartTestType,
)

logger = logging.getLogger(__name__)

SMARTCTL_BIN = "/usr/sbin/smartctl"

# Critical SMART attribute IDs for ATA drives
CRITICAL_ATTR_IDS = {
    5: "Reallocated_Sector_Ct",
    187: "Reported_Uncorrect",
    188: "Command_Timeout",
    196: "Reallocated_Event_Count",
    197: "Current_Pending_Sector",
    198: "Offline_Uncorrectable",
}


def _run_cmd(cmd: List[str], check: bool = False) -> subprocess.CompletedProcess:
    logger.debug("Executing SMART command: %s", " ".join(cmd))
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


class SmartService:
    """Service to handle S.M.A.R.T. monitoring and self-testing for drives."""

    def __init__(self, smartctl_bin: str = SMARTCTL_BIN, history_dir: str = "/var/log/naybinho/smart"):
        self.smartctl_bin = smartctl_bin
        self.history_dir = Path(history_dir)
        try:
            self.history_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def get_drive_health(self, device: str) -> SmartReport:
        """
        Gathers SMART attributes using smartctl --json and evaluates health status:
        Good / Warning / Critical / Failed.
        """
        report = SmartReport(device=device)

        # First try smartctl -x --json
        cmd = [self.smartctl_bin, "-x", "--json", device]
        res = _run_cmd(cmd)

        if res.returncode not in (0, 1, 2, 4, 8) and not res.stdout:
            # Fallback to standard text output parsing if json fails or not supported
            return self._parse_text_smartctl(device)

        try:
            data = json.loads(res.stdout)
            return self._parse_json_smartctl(device, data, res.stdout)
        except Exception as e:
            logger.warning("Failed parsing smartctl JSON for %s (%s), falling back to text parsing", device, e)
            return self._parse_text_smartctl(device)

    def _parse_json_smartctl(self, device: str, data: dict, raw_json: str) -> SmartReport:
        device_info = data.get("device", {})
        smart_status = data.get("smart_status", {})
        temperature_info = data.get("temperature", {})
        power_cycle_info = data.get("power_cycle_count")
        power_on_time = data.get("power_on_time", {})

        report = SmartReport(
            device=device,
            model=data.get("model_name"),
            serial=data.get("serial_number"),
            firmware=data.get("firmware_version"),
            capacity_bytes=data.get("user_capacity", {}).get("bytes"),
            smart_enabled=data.get("smart_support", {}).get("enabled", False),
            raw_output=raw_json,
            collected_at=datetime.utcnow()
        )

        # Temperature
        if "current" in temperature_info:
            report.temperature_celsius = float(temperature_info["current"])

        # Power On Hours / Cycles
        if "hours" in power_on_time:
            report.power_on_hours = int(power_on_time["hours"])
        if power_cycle_info is not None:
            report.power_cycle_count = int(power_cycle_info)

        # ATA Attributes parsing
        ata_table = data.get("ata_smart_attributes", {}).get("table", [])
        for item in ata_table:
            attr_id = item.get("id")
            attr_name = item.get("name", "Unknown")
            val = item.get("value", 0)
            worst = item.get("worst", 0)
            thresh = item.get("thresh", 0)
            raw = item.get("raw", {}).get("value", 0)
            raw_str = item.get("raw", {}).get("string", str(raw))
            when_failed = item.get("when_failed")

            is_crit = attr_id in CRITICAL_ATTR_IDS
            attr = SmartAttribute(
                id=attr_id,
                name=attr_name,
                value=val,
                worst=worst,
                threshold=thresh,
                raw_value=raw,
                raw_string=raw_str,
                when_failed=when_failed,
                is_critical=is_crit,
            )
            report.attributes.append(attr)

            if attr_id == 5:
                report.reallocated_sectors = raw
            elif attr_id == 197:
                report.pending_sectors = raw
            elif attr_id in (187, 198):
                report.uncorrectable_errors += raw

        # NVMe SMART parsing
        nvme_attributes = data.get("nvme_smart_health_information_log", {})
        if nvme_attributes:
            report.temperature_celsius = float(nvme_attributes.get("temperature", report.temperature_celsius or 0))
            report.power_on_hours = nvme_attributes.get("power_on_hours", report.power_on_hours)
            report.power_cycle_count = nvme_attributes.get("power_cycles", report.power_cycle_count)
            report.uncorrectable_errors = nvme_attributes.get("media_errors", 0)

        # Self-test log parsing
        test_entries = data.get("ata_smart_self_test_log", {}).get("standard", {}).get("table", [])
        for entry in test_entries:
            desc = entry.get("type", {}).get("string", "").lower()
            status_desc = entry.get("status", {}).get("string", "").lower()

            t_type = SmartTestType.SHORT if "short" in desc else SmartTestType.LONG
            if "completed without error" in status_desc:
                t_stat = SmartTestStatus.PASSED
            elif "in progress" in status_desc:
                t_stat = SmartTestStatus.IN_PROGRESS
            elif "aborted" in status_desc:
                t_stat = SmartTestStatus.ABORTED
            else:
                t_stat = SmartTestStatus.FAILED

            report.tests.append(
                SmartTest(
                    test_type=t_type,
                    status=t_stat,
                    lifetime_hours=entry.get("lifetime_hours"),
                    lba_of_first_error=str(entry.get("lba_of_first_error")) if entry.get("lba_of_first_error") else None
                )
            )

        # Compute health classification
        passed = smart_status.get("passed", True)
        self._classify_health(report, passed)

        self._record_history(report)
        return report

    def _parse_text_smartctl(self, device: str) -> SmartReport:
        cmd = [self.smartctl_bin, "-a", device]
        res = _run_cmd(cmd)

        report = SmartReport(
            device=device,
            raw_output=res.stdout,
            collected_at=datetime.utcnow()
        )

        passed = True
        for line in res.stdout.splitlines():
            line = line.strip()
            if "Device Model:" in line or "Model Number:" in line:
                report.model = line.split(":", 1)[1].strip()
            elif "Serial Number:" in line:
                report.serial = line.split(":", 1)[1].strip()
            elif "Firmware Version:" in line:
                report.firmware = line.split(":", 1)[1].strip()
            elif "User Capacity:" in line:
                bytes_match = re.search(r"([\d,]+)\s+bytes", line)
                if bytes_match:
                    report.capacity_bytes = int(bytes_match.group(1).replace(",", ""))
            elif "SMART overall-health self-assessment test result:" in line:
                status_str = line.split(":", 1)[1].strip()
                passed = ("PASSED" in status_str or "OK" in status_str)
            elif "SMART Health Status:" in line:
                status_str = line.split(":", 1)[1].strip()
                passed = ("OK" in status_str or "PASSED" in status_str)
            elif re.match(r"^\d+\s+\w+", line):
                parts = line.split()
                if len(parts) >= 10:
                    try:
                        attr_id = int(parts[0])
                        attr_name = parts[1]
                        val = int(parts[3])
                        worst = int(parts[4])
                        thresh = int(parts[5])
                        raw = int(parts[9])

                        is_crit = attr_id in CRITICAL_ATTR_IDS
                        report.attributes.append(
                            SmartAttribute(
                                id=attr_id,
                                name=attr_name,
                                value=val,
                                worst=worst,
                                threshold=thresh,
                                raw_value=raw,
                                is_critical=is_crit
                            )
                        )
                        if attr_id == 5:
                            report.reallocated_sectors = raw
                        elif attr_id == 194:
                            report.temperature_celsius = float(raw)
                        elif attr_id == 197:
                            report.pending_sectors = raw
                        elif attr_id in (187, 198):
                            report.uncorrectable_errors += raw
                        elif attr_id == 9:
                            report.power_on_hours = raw
                        elif attr_id == 12:
                            report.power_cycle_count = raw
                    except Exception:
                        pass

        self._classify_health(report, passed)
        self._record_history(report)
        return report

    def _classify_health(self, report: SmartReport, self_assess_passed: bool) -> None:
        """Classify health into Good / Warning / Critical / Failed."""
        if not self_assess_passed:
            report.overall_health = SmartHealth.FAILED
            report.overall_assessment = "Falha iminente detectada pelo autodiagnóstico SMART do disco."
            return

        reallocated = report.reallocated_sectors
        pending = report.pending_sectors
        uncorrectable = report.uncorrectable_errors
        temp = report.temperature_celsius or 0.0

        if reallocated > 100 or pending > 50 or uncorrectable > 20:
            report.overall_health = SmartHealth.CRITICAL
            report.overall_assessment = (
                f"Estado crítico: {reallocated} setores realocados, {pending} setores pendentes, "
                f"{uncorrectable} erros incorrigíveis. Faça backup imediatamente e substitua o disco."
            )
        elif reallocated > 5 or pending > 0 or uncorrectable > 0 or temp >= 55.0:
            report.overall_health = SmartHealth.WARNING
            msg_parts = []
            if reallocated > 0:
                msg_parts.append(f"{reallocated} setores realocados")
            if pending > 0:
                msg_parts.append(f"{pending} setores pendentes")
            if uncorrectable > 0:
                msg_parts.append(f"{uncorrectable} erros incorrigíveis")
            if temp >= 55.0:
                msg_parts.append(f"temperatura elevada ({temp}°C)")
            report.overall_assessment = f"Atenção necessária: {', '.join(msg_parts)}."
        else:
            report.overall_health = SmartHealth.GOOD
            report.overall_assessment = "Disco saudável. Todos os parâmetros operacionais normais."

    def run_self_test(self, device: str, test_type: SmartTestType) -> OperationResult:
        """Triggers a background short or long SMART test via smartctl."""
        mode = "short" if test_type == SmartTestType.SHORT else "long"
        cmd = [self.smartctl_bin, f"-t", mode, device]
        res = _run_cmd(cmd)

        if res.returncode == 0 or "has begun" in res.stdout or "Testing has begun" in res.stdout:
            return OperationResult(
                success=True,
                message=f"Teste SMART ({mode}) iniciado com sucesso em {device}.",
                details={"device": device, "type": mode, "output": res.stdout.strip()}
            )

        return OperationResult(
            success=False,
            message=f"Falha ao iniciar teste SMART ({mode}) em {device}.",
            error=res.stderr or res.stdout
        )

    def abort_self_test(self, device: str) -> OperationResult:
        """Aborts an active SMART self-test."""
        cmd = [self.smartctl_bin, "-X", device]
        res = _run_cmd(cmd)
        if res.returncode == 0:
            return OperationResult(
                success=True,
                message=f"Teste SMART abortado em {device}.",
                details={"device": device}
            )
        return OperationResult(
            success=False,
            message=f"Não foi possível abortar teste em {device}.",
            error=res.stderr or res.stdout
        )

    def _record_history(self, report: SmartReport) -> None:
        """Stores historical snapshot in JSON lines format."""
        try:
            dev_slug = Path(report.device).name
            hist_file = self.history_dir / f"{dev_slug}_history.jsonl"
            payload = {
                "timestamp": report.collected_at.isoformat(),
                "device": report.device,
                "health": report.overall_health.value,
                "reallocated": report.reallocated_sectors,
                "pending": report.pending_sectors,
                "uncorrectable": report.uncorrectable_errors,
                "temperature": report.temperature_celsius,
                "power_on_hours": report.power_on_hours
            }
            with open(hist_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(payload) + "\n")
        except Exception as e:
            logger.debug("History write skipped: %s", e)

    def get_history(self, device: str, limit: int = 50) -> List[Dict]:
        """Reads historical SMART readings for a device."""
        dev_slug = Path(device).name
        hist_file = self.history_dir / f"{dev_slug}_history.jsonl"
        if not hist_file.exists():
            return []
        lines = hist_file.read_text(encoding="utf-8").strip().splitlines()
        results = []
        for line in lines[-limit:]:
            try:
                results.append(json.loads(line))
            except Exception:
                pass
        return results


smart_service = SmartService()
