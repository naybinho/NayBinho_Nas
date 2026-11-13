#!/usr/bin/env bash
# =============================================================================
# NayBinho NAS — Script de Backup Automático
# Faz backup das configurações, banco de dados e dados críticos
# =============================================================================
set -euo pipefail

# ── Configurações ─────────────────────────────────────────────────────────────
NAYBINHO_HOME="${NAYBINHO_HOME:-/opt/naybinho}"
NAYBINHO_DATA="${NAYBINHO_DATA:-/var/lib/naybinho}"
NAYBINHO_LOGS="${NAYBINHO_LOGS:-/var/log/naybinho}"
BACKUP_DIR="${BACKUP_DIR:-${NAYBINHO_DATA}/backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_NAME="naybinho-backup-${TIMESTAMP}"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"

# Log de backup
LOG_FILE="${NAYBINHO_LOGS}/backup.log"

# ── Cores ─────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'

# ── Funções ───────────────────────────────────────────────────────────────────
log()   { local msg="[$(date +'%Y-%m-%d %H:%M:%S')] [INFO]  $*"; echo -e "${GREEN}${msg}${NC}"; echo "$msg" >> "$LOG_FILE" 2>/dev/null || true; }
warn()  { local msg="[$(date +'%Y-%m-%d %H:%M:%S')] [WARN]  $*"; echo -e "${YELLOW}${msg}${NC}"; echo "$msg" >> "$LOG_FILE" 2>/dev/null || true; }
error() { local msg="[$(date +'%Y-%m-%d %H:%M:%S')] [ERROR] $*"; echo -e "${RED}${msg}${NC}" >&2; echo "$msg" >> "$LOG_FILE" 2>/dev/null || true; }
die()   { error "$*"; exit 1; }

# ── Verificações ──────────────────────────────────────────────────────────────
check_requirements() {
    [[ $EUID -eq 0 ]] || die "Execute como root: sudo bash backup.sh"
    command -v tar &>/dev/null || die "tar não encontrado"
    mkdir -p "$BACKUP_DIR" "$NAYBINHO_LOGS"
}

# ── Backup de configurações ───────────────────────────────────────────────────
backup_configs() {
    log "Fazendo backup das configurações..."
    local config_backup="${BACKUP_PATH}/configs"
    mkdir -p "$config_backup"

    # Configurações do NayBinho
    [[ -d "${NAYBINHO_HOME}/config" ]] && \
        cp -r "${NAYBINHO_HOME}/config/" "${config_backup}/naybinho/" 2>/dev/null || true

    # Arquivos de sistema
    [[ -d "${NAYBINHO_HOME}/system" ]] && \
        cp -r "${NAYBINHO_HOME}/system/" "${config_backup}/system/" 2>/dev/null || true

    # Configurações do sistema operacional
    for f in /etc/hostname /etc/hosts /etc/fstab /etc/mdadm/mdadm.conf; do
        [[ -f "$f" ]] && cp "$f" "${config_backup}/" 2>/dev/null || true
    done

    # Nginx
    [[ -d /etc/nginx/conf.d ]] && \
        cp -r /etc/nginx/conf.d/ "${config_backup}/nginx-conf.d/" 2>/dev/null || true

    # Samba
    [[ -f /etc/samba/smb.conf ]] && \
        cp /etc/samba/smb.conf "${config_backup}/smb.conf" 2>/dev/null || true

    # NFS
    [[ -f /etc/exports ]] && \
        cp /etc/exports "${config_backup}/exports" 2>/dev/null || true

    # Crontab
    crontab -l > "${config_backup}/crontab.txt" 2>/dev/null || true

    # Serviços systemd do naybinho
    cp /etc/systemd/system/naybinho-*.service "${config_backup}/" 2>/dev/null || true
    cp /etc/systemd/system/naybinho-*.timer "${config_backup}/" 2>/dev/null || true

    log "Configurações salvas em ${config_backup}"
}

# ── Backup do banco de dados ──────────────────────────────────────────────────
backup_database() {
    log "Fazendo backup do banco de dados..."
    local db_backup="${BACKUP_PATH}/database"
    mkdir -p "$db_backup"

    local db_file="${NAYBINHO_DATA}/db/naybinho.db"
    if [[ -f "$db_file" ]]; then
        # Backup com SQLite3 (dump seguro)
        if command -v sqlite3 &>/dev/null; then
            sqlite3 "$db_file" ".backup '${db_backup}/naybinho.db'" 2>/dev/null || \
                cp "$db_file" "${db_backup}/naybinho.db"
        else
            cp "$db_file" "${db_backup}/naybinho.db"
        fi
        log "Banco de dados copiado"
    else
        warn "Banco de dados não encontrado em $db_file"
    fi
}

# ── Backup dos dados ──────────────────────────────────────────────────────────
backup_data() {
    log "Fazendo backup dos dados de uploads..."
    local data_backup="${BACKUP_PATH}/data"
    mkdir -p "$data_backup"

    # Uploads (com limite de tamanho para não estourar espaço)
    if [[ -d "${NAYBINHO_DATA}/uploads" ]]; then
        local uploads_size
        uploads_size=$(du -sm "${NAYBINHO_DATA}/uploads" 2>/dev/null | cut -f1 || echo 0)
        if [[ $uploads_size -lt 500 ]]; then
            cp -r "${NAYBINHO_DATA}/uploads/" "${data_backup}/uploads/" 2>/dev/null || true
        else
            warn "Pasta uploads muito grande (${uploads_size}MB), pulando..."
        fi
    fi
}

# ── Backup externo (rclone) ───────────────────────────────────────────────────
backup_remote() {
    local remote="${RCLONE_REMOTE:-}"
    if [[ -z "$remote" ]] || ! command -v rclone &>/dev/null; then
        return
    fi

    log "Enviando backup para armazenamento remoto: $remote..."
    rclone copy "${BACKUP_PATH}.tar.gz" "${remote}:naybinho-backups/" \
        --progress \
        --transfers 4 \
        2>/dev/null || warn "Falha no backup remoto"
}

# ── Compactar backup ──────────────────────────────────────────────────────────
compress_backup() {
    log "Compactando backup..."
    tar -czf "${BACKUP_PATH}.tar.gz" -C "$BACKUP_DIR" "$BACKUP_NAME"
    rm -rf "$BACKUP_PATH"

    local size
    size=$(du -sh "${BACKUP_PATH}.tar.gz" | cut -f1)
    log "Backup compactado: ${BACKUP_PATH}.tar.gz (${size})"
}

# ── Verificar integridade ─────────────────────────────────────────────────────
verify_backup() {
    log "Verificando integridade do backup..."
    if tar -tzf "${BACKUP_PATH}.tar.gz" > /dev/null 2>&1; then
        # Gerar checksum
        sha256sum "${BACKUP_PATH}.tar.gz" > "${BACKUP_PATH}.tar.gz.sha256"
        log "Backup verificado com sucesso. Checksum salvo."
    else
        error "Backup corrompido! Arquivo: ${BACKUP_PATH}.tar.gz"
        rm -f "${BACKUP_PATH}.tar.gz"
        exit 1
    fi
}

# ── Limpar backups antigos ────────────────────────────────────────────────────
cleanup_old_backups() {
    log "Removendo backups com mais de ${BACKUP_RETENTION_DAYS} dias..."
    find "$BACKUP_DIR" -name "naybinho-backup-*.tar.gz" -mtime "+${BACKUP_RETENTION_DAYS}" -delete 2>/dev/null || true
    find "$BACKUP_DIR" -name "naybinho-backup-*.sha256" -mtime "+${BACKUP_RETENTION_DAYS}" -delete 2>/dev/null || true

    # Listar backups mantidos
    local count
    count=$(find "$BACKUP_DIR" -name "naybinho-backup-*.tar.gz" | wc -l)
    log "$count backup(s) mantido(s) em $BACKUP_DIR"
}

# ── Relatório ─────────────────────────────────────────────────────────────────
print_report() {
    echo ""
    echo -e "${GREEN}${BOLD}═══ Backup Concluído ═══${NC}"
    echo -e "  Arquivo:    ${CYAN}${BACKUP_PATH}.tar.gz${NC}"
    echo -e "  Tamanho:    ${CYAN}$(du -sh "${BACKUP_PATH}.tar.gz" | cut -f1)${NC}"
    echo -e "  Timestamp:  ${CYAN}${TIMESTAMP}${NC}"
    echo -e "  Retenção:   ${CYAN}${BACKUP_RETENTION_DAYS} dias${NC}"
    echo ""
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
    log "═══ Iniciando backup do NayBinho NAS ═══"

    check_requirements

    mkdir -p "$BACKUP_PATH"

    backup_configs
    backup_database
    backup_data
    compress_backup
    verify_backup
    backup_remote
    cleanup_old_backups
    print_report

    log "═══ Backup finalizado com sucesso ═══"
}

main "$@"
