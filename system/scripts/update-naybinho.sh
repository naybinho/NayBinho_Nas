#!/usr/bin/env bash
# =============================================================================
# NayBinho NAS — Script de Atualização
# Atualiza o NayBinho NAS para uma nova versão
# =============================================================================
set -euo pipefail

# ── Configurações ─────────────────────────────────────────────────────────────
NAYBINHO_HOME="${NAYBINHO_HOME:-/opt/naybinho}"
NAYBINHO_DATA="${NAYBINHO_DATA:-/var/lib/naybinho}"
NAYBINHO_LOGS="${NAYBINHO_LOGS:-/var/log/naybinho}"
NAYBINHO_USER="${NAYBINHO_USER:-naybinho}"
UPDATE_LOG="${NAYBINHO_LOGS}/update.log"
GITHUB_REPO="${GITHUB_REPO:-naybinho/nas}"
GITHUB_API="https://api.github.com/repos/${GITHUB_REPO}/releases/latest"
TEMP_DIR=$(mktemp -d)
CHECK_ONLY=false

# ── Cores ─────────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

log()   { local msg="[$(date +'%Y-%m-%d %H:%M:%S')] [INFO]  $*"; echo -e "${GREEN}${msg}${NC}"; echo "$msg" >> "$UPDATE_LOG" 2>/dev/null || true; }
warn()  { local msg="[$(date +'%Y-%m-%d %H:%M:%S')] [WARN]  $*"; echo -e "${YELLOW}${msg}${NC}"; echo "$msg" >> "$UPDATE_LOG" 2>/dev/null || true; }
error() { local msg="[$(date +'%Y-%m-%d %H:%M:%S')] [ERROR] $*"; echo -e "${RED}${msg}${NC}" >&2; echo "$msg" >> "$UPDATE_LOG" 2>/dev/null || true; }
info()  { echo -e "${BLUE}[i]${NC} $*"; }
die()   { error "$*"; cleanup; exit 1; }

# ── Limpeza ───────────────────────────────────────────────────────────────────
cleanup() {
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

# ── Versão atual ──────────────────────────────────────────────────────────────
get_current_version() {
    local version_file="${NAYBINHO_HOME}/VERSION"
    if [[ -f "$version_file" ]]; then
        cat "$version_file"
    else
        echo "0.0.0"
    fi
}

# ── Verificar nova versão ─────────────────────────────────────────────────────
check_latest_version() {
    local latest_version latest_url

    if ! command -v curl &>/dev/null && ! command -v wget &>/dev/null; then
        warn "curl/wget não disponível. Não foi possível verificar atualizações."
        return 1
    fi

    info "Verificando versão mais recente..."

    if command -v curl &>/dev/null; then
        local response
        response=$(curl -sf --max-time 15 "$GITHUB_API" 2>/dev/null) || {
            warn "Falha ao verificar atualizações (sem internet ou API indisponível)"
            return 1
        }
        latest_version=$(echo "$response" | grep '"tag_name"' | cut -d'"' -f4 | tr -d 'v')
        latest_url=$(echo "$response" | grep '"browser_download_url".*\.tar\.gz"' | head -1 | cut -d'"' -f4)
    fi

    echo "$latest_version|$latest_url"
}

# ── Comparar versões ──────────────────────────────────────────────────────────
version_gt() {
    # Retorna true se $1 > $2
    [[ "$1" == "$2" ]] && return 1
    local IFS=.
    local i ver1=($1) ver2=($2)
    for ((i=0; i<${#ver1[@]}; i++)); do
        if [[ -z ${ver2[i]+x} ]]; then ver2[i]=0; fi
        if ((10#${ver1[i]} > 10#${ver2[i]})); then return 0; fi
        if ((10#${ver1[i]} < 10#${ver2[i]})); then return 1; fi
    done
    return 1
}

# ── Fazer backup antes de atualizar ──────────────────────────────────────────
pre_update_backup() {
    log "Fazendo backup pré-atualização..."
    if [[ -x "${NAYBINHO_HOME}/system/scripts/backup.sh" ]]; then
        bash "${NAYBINHO_HOME}/system/scripts/backup.sh" || warn "Backup pré-atualização falhou"
    fi
}

# ── Baixar nova versão ────────────────────────────────────────────────────────
download_update() {
    local url="$1"
    local archive="${TEMP_DIR}/naybinho-update.tar.gz"

    info "Baixando atualização de: $url"
    if ! curl -fL --progress-bar --max-time 300 -o "$archive" "$url"; then
        die "Falha ao baixar atualização"
    fi

    # Verificar integridade
    if ! tar -tzf "$archive" > /dev/null 2>&1; then
        die "Arquivo de atualização corrompido"
    fi

    log "Download concluído"
    echo "$archive"
}

# ── Aplicar atualização ───────────────────────────────────────────────────────
apply_update() {
    local archive="$1"
    local new_version="$2"

    log "Aplicando atualização para v${new_version}..."

    # Extrair
    tar -xzf "$archive" -C "$TEMP_DIR"
    local extracted_dir
    extracted_dir=$(find "$TEMP_DIR" -maxdepth 1 -type d -name "naybinho-*" | head -1)
    [[ -n "$extracted_dir" ]] || die "Estrutura do pacote inválida"

    # Parar serviços
    log "Parando serviços..."
    systemctl stop naybinho-backend naybinho-monitor 2>/dev/null || true
    sleep 2

    # Atualizar backend
    if [[ -d "${extracted_dir}/backend" ]]; then
        rsync -a --exclude '__pycache__' --exclude '*.pyc' \
            "${extracted_dir}/backend/" "${NAYBINHO_HOME}/backend/"
        log "Backend atualizado"
    fi

    # Atualizar frontend
    if [[ -d "${extracted_dir}/frontend/dist" ]]; then
        rsync -a "${extracted_dir}/frontend/dist/" "${NAYBINHO_HOME}/frontend/dist/"
        log "Frontend atualizado"
    fi

    # Atualizar scripts do sistema
    if [[ -d "${extracted_dir}/system" ]]; then
        rsync -a "${extracted_dir}/system/" "${NAYBINHO_HOME}/system/"
        chmod +x "${NAYBINHO_HOME}/system/scripts/"*.sh
        log "Scripts do sistema atualizados"
    fi

    # Atualizar dependências Python
    log "Atualizando dependências Python..."
    "${NAYBINHO_HOME}/venv/bin/pip" install \
        -r "${NAYBINHO_HOME}/backend/requirements.txt" \
        --quiet --upgrade

    # Ajustar permissões
    chown -R "${NAYBINHO_USER}:${NAYBINHO_USER}" "${NAYBINHO_HOME}"

    # Atualizar version file
    echo "$new_version" > "${NAYBINHO_HOME}/VERSION"

    # Recarregar e reiniciar serviços
    systemctl daemon-reload
    systemctl start naybinho-backend naybinho-monitor 2>/dev/null || warn "Falha ao reiniciar serviços"
    systemctl reload nginx 2>/dev/null || true

    log "Atualização para v${new_version} aplicada com sucesso"
}

# ── Rollback ──────────────────────────────────────────────────────────────────
rollback() {
    warn "Executando rollback..."
    # TODO: restaurar backup mais recente
    local latest_backup
    latest_backup=$(find "${NAYBINHO_DATA}/backups" -name "*.tar.gz" -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2)
    if [[ -n "$latest_backup" ]]; then
        info "Backup disponível: $latest_backup"
        info "Execute: bash ${NAYBINHO_HOME}/system/scripts/backup.sh restore $latest_backup"
    fi
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
    # Processar argumentos
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --check-only) CHECK_ONLY=true; shift ;;
            --force) FORCE=true; shift ;;
            *) warn "Argumento desconhecido: $1"; shift ;;
        esac
    done

    mkdir -p "$NAYBINHO_LOGS"

    local current_version
    current_version=$(get_current_version)

    echo -e "\n${BOLD}${CYAN}═══ NayBinho NAS Updater ═══${NC}"
    echo -e "  Versão atual: ${CYAN}${current_version}${NC}"

    # Verificar nova versão
    local version_info
    version_info=$(check_latest_version) || {
        # Atualizar apenas pacotes do sistema se não conseguir verificar
        if [[ "$CHECK_ONLY" == false ]]; then
            log "Atualizando pacotes do sistema Ubuntu..."
            apt-get update -qq && apt-get upgrade -y --no-install-recommends 2>/dev/null || true
        fi
        exit 0
    }

    local latest_version latest_url
    latest_version=$(echo "$version_info" | cut -d'|' -f1)
    latest_url=$(echo "$version_info" | cut -d'|' -f2)

    echo -e "  Versão mais recente: ${CYAN}${latest_version}${NC}"

    if ! version_gt "$latest_version" "$current_version"; then
        log "NayBinho NAS já está na versão mais recente (${current_version})"
        exit 0
    fi

    echo -e "\n  ${GREEN}✓ Nova versão disponível: ${latest_version}${NC}"

    if [[ "$CHECK_ONLY" == true ]]; then
        # Apenas notificar via API do backend
        curl -sf -X POST "http://localhost:8000/api/notifications" \
            -H "Content-Type: application/json" \
            -d "{\"type\": \"update_available\", \"version\": \"${latest_version}\"}" \
            2>/dev/null || true
        exit 0
    fi

    # Confirmar atualização se interativo
    if [[ -t 0 ]]; then
        read -rp "$(echo -e "${YELLOW}Atualizar de ${current_version} para ${latest_version}? [s/N]:${NC} ")" ans
        [[ "${ans,,}" == "s" ]] || { info "Cancelado."; exit 0; }
    fi

    [[ $EUID -eq 0 ]] || die "Atualização requer root: sudo bash update-naybinho.sh"

    pre_update_backup

    local archive
    archive=$(download_update "$latest_url")

    if ! apply_update "$archive" "$latest_version"; then
        rollback
        die "Falha na atualização"
    fi

    log "NayBinho NAS atualizado para v${latest_version} com sucesso!"
}

main "$@"
