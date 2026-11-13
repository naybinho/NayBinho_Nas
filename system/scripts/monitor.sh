#!/usr/bin/env bash
# =============================================================================
# NayBinho NAS — Script de Monitoramento do Sistema
# Monitora: Saúde dos Discos (SMART), Temperatura, Status RAID, Espaço em Disco
# Envia alertas via webhook / logs / API local do NayBinho NAS
# =============================================================================
set -euo pipefail

# ── Configurações e Defaults ──────────────────────────────────────────────────
CONFIG_FILE="${NAYBINHO_CONFIG:-/opt/naybinho/config/naybinho.conf}"
LOG_FILE="/var/log/naybinho/monitor.log"
STATE_FILE="/var/lib/naybinho/monitor_state.json"
INTERVAL=60
DAEMON_MODE=false

TEMP_WARN_THRESHOLD=50
TEMP_CRIT_THRESHOLD=60
DISK_USAGE_WARN_THRESHOLD=85
DISK_USAGE_CRIT_THRESHOLD=95

API_ENDPOINT="http://127.0.0.1:8000/api/system/alerts"

# Parse CLI arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --daemon)
            DAEMON_MODE=true
            shift
            ;;
        --interval)
            INTERVAL="$2"
            shift 2
            ;;
        --config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

mkdir -p "$(dirname "$LOG_FILE")" "$(dirname "$STATE_FILE")" 2>/dev/null || true

# ── Logging & Alerting ────────────────────────────────────────────────────────
log() {
    local level="$1"; shift
    local msg="[$(date +'%Y-%m-%d %H:%M:%S')] [$level] $*"
    echo "$msg"
    echo "$msg" >> "$LOG_FILE" 2>/dev/null || true
}

send_alert() {
    local severity="$1" # info, warning, critical
    local source="$2"   # smart, temp, raid, disk
    local message="$3"

    log "$severity" "[$source] $message"

    # Envia alerta para o backend se estiver rodando
    if command -v curl &>/dev/null; then
        local payload
        payload=$(jq -n \
            --arg sev "$severity" \
            --arg src "$source" \
            --arg msg "$message" \
            --arg time "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
            '{severity: $sev, source: $src, message: $msg, timestamp: $time}' 2>/dev/null || true)

        if [[ -n "$payload" ]]; then
            curl -s -X POST "$API_ENDPOINT" \
                -H "Content-Type: application/json" \
                -d "$payload" \
                --connect-timeout 2 \
                --max-time 4 >/dev/null 2>&1 || true
        fi
    fi
}

# ── 1. Monitorar Status do RAID (mdadm / zfs) ─────────────────────────────────
check_raid() {
    # 1.1 Linux Software RAID (mdadm)
    if [[ -f /proc/mdstat ]]; then
        if grep -q "blocks" /proc/mdstat; then
            for md_path in /dev/md*; do
                [[ -b "$md_path" ]] || continue
                local md_name
                md_name=$(basename "$md_path")

                if command -v mdadm &>/dev/null; then
                    local detail
                    detail=$(mdadm --detail "$md_path" 2>/dev/null || true)
                    if [[ -n "$detail" ]]; then
                        local state
                        state=$(echo "$detail" | grep -E "^\s*State :" | awk -F: '{print $2}' | xargs)
                        local failed_devs
                        failed_devs=$(echo "$detail" | grep -E "^\s*Failed Devices :" | awk -F: '{print $2}' | xargs)

                        if [[ "$state" =~ "degraded" ]]; then
                            send_alert "critical" "raid" "Array $md_name está DEGRADADO! Estado: $state. Discos falhos: $failed_devs"
                        elif [[ "$state" =~ "recovering" || "$state" =~ "resync" ]]; then
                            send_alert "warning" "raid" "Array $md_name em reconstrução/sincronização ($state)"
                        elif [[ -n "$failed_devs" && "$failed_devs" -gt 0 ]]; then
                            send_alert "critical" "raid" "Array $md_name possui $failed_devs dispositivo(s) em falha!"
                        fi
                    fi
                fi
            done
        fi
    fi

    # 1.2 ZFS Pools (se instalado e em uso)
    if command -v zpool &>/dev/null; then
        local zfs_status
        zfs_status=$(zpool status -x 2>/dev/null || true)
        if [[ -n "$zfs_status" && "$zfs_status" != "all pools are healthy" ]]; then
            send_alert "critical" "raid" "Pool ZFS com erro: $zfs_status"
        fi
    fi
}

# ── 2. Monitorar SMART e Temperaturas dos Discos ───────────────────────────────
check_disks_smart_and_temp() {
    # Lista discos excluindo partições, loops e ramdisks
    local disks
    disks=$(lsblk -d -n -o NAME,TYPE 2>/dev/null | awk '$2=="disk"{print $1}' | grep -v '^loop\|^ram\|^zram' || true)

    for disk in $disks; do
        local dev="/dev/$disk"
        [[ -b "$dev" ]] || continue

        # 2.1 SMART Health Check
        if command -v smartctl &>/dev/null; then
            local smart_info
            smart_info=$(smartctl -H "$dev" 2>/dev/null || true)

            if echo "$smart_info" | grep -iq "FAILED!"; then
                send_alert "critical" "smart" "Disco $dev FALHOU no teste de integridade SMART!"
            elif echo "$smart_info" | grep -iq "PASSED" || echo "$smart_info" | grep -iq "OK"; then
                : # Disco saudável
            fi

            # 2.2 Temperatura via smartctl
            local temp
            temp=$(smartctl -A "$dev" 2>/dev/null | awk '/Temperature_Celsius|Current Drive Temperature|Airflow_Temperature/ {print $10}' | head -n1 || true)
            
            # Para discos NVMe
            if [[ -z "$temp" && "$disk" =~ ^nvme ]]; then
                temp=$(smartctl -A "$dev" 2>/dev/null | grep -i "Temperature:" | awk '{print $2}' | head -n1 || true)
            fi

            if [[ -n "$temp" && "$temp" =~ ^[0-9]+$ ]]; then
                if (( temp >= TEMP_CRIT_THRESHOLD )); then
                    send_alert "critical" "temp" "Temperatura crítica no disco $dev: ${temp}°C (Limite: ${TEMP_CRIT_THRESHOLD}°C)"
                elif (( temp >= TEMP_WARN_THRESHOLD )); then
                    send_alert "warning" "temp" "Temperatura elevada no disco $dev: ${temp}°C (Alerta: ${TEMP_WARN_THRESHOLD}°C)"
                fi
            fi
        fi
    done

    # 2.3 Temperatura da CPU via lm-sensors / sysfs
    if [[ -d /sys/class/thermal ]]; then
        for zone in /sys/class/thermal/thermal_zone*; do
            if [[ -f "$zone/temp" ]]; then
                local raw_temp
                raw_temp=$(cat "$zone/temp" 2>/dev/null || echo 0)
                local cpu_temp=$(( raw_temp / 1000 ))
                local zone_type
                zone_type=$(cat "$zone/type" 2>/dev/null || echo "zone")

                if (( cpu_temp >= 85 )); then
                    send_alert "critical" "temp" "Temperatura da CPU/Sistema ($zone_type) crítica: ${cpu_temp}°C"
                elif (( cpu_temp >= 75 )); then
                    send_alert "warning" "temp" "Temperatura da CPU/Sistema ($zone_type) alta: ${cpu_temp}°C"
                fi
            fi
        done
    fi
}

# ── 3. Monitorar Uso do Espaço em Disco ────────────────────────────────────────
check_disk_usage() {
    # Verifica todos os filesystems locais montados
    df -PTh 2>/dev/null | awk 'NR>1 {print $1, $2, $6, $7}' | while read -r fs type use mount; do
        # Ignora squashfs, tmpfs, devtmpfs, overlays do docker
        if [[ "$type" =~ ^(tmpfs|devtmpfs|squashfs|overlay)$ ]] || [[ "$mount" =~ ^/(boot|var/lib/docker) ]]; then
            continue
        fi

        local percent="${use%\%}"
        if [[ "$percent" =~ ^[0-9]+$ ]]; then
            if (( percent >= DISK_USAGE_CRIT_THRESHOLD )); then
                send_alert "critical" "disk" "Partição $mount ($fs) com uso crítico: ${percent}%!"
            elif (( percent >= DISK_USAGE_WARN_THRESHOLD )); then
                send_alert "warning" "disk" "Partição $mount ($fs) atingiu uso elevado: ${percent}%"
            fi
        fi
    done
}

# ── 4. Ciclo de Execução ──────────────────────────────────────────────────────
run_checks() {
    log "INFO" "Executando ciclo de monitoramento..."
    check_raid
    check_disks_smart_and_temp
    check_disk_usage
}

if [ "$DAEMON_MODE" = true ]; then
    log "INFO" "Iniciando monitoramento contínuo NayBinho NAS (Intervalo: ${INTERVAL}s)..."
    while true; do
        run_checks || log "ERROR" "Erro ao executar checagens de monitoramento."
        sleep "$INTERVAL"
    done
else
    run_checks
fi
