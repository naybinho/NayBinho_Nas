#!/usr/bin/env bash
# =============================================================================
# NayBinho NAS — Script de Instalação Completo
# Versão: 1.0.0
# Suporte: Ubuntu 26.04 LTS (Noble Numbat / ou próxima LTS)
# =============================================================================
set -euo pipefail
IFS=$'\n\t'

# ── Cores ────────────────────────────────────────────────────────────────────
RED='\033[0;31m';    GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m';   CYAN='\033[0;36m';  BOLD='\033[1m'; NC='\033[0m'

# ── Configurações ─────────────────────────────────────────────────────────────
NAYBINHO_VERSION="1.0.0"
NAYBINHO_USER="naybinho"
NAYBINHO_GROUP="naybinho"
NAYBINHO_HOME="/opt/naybinho"
NAYBINHO_DATA="/var/lib/naybinho"
NAYBINHO_LOGS="/var/log/naybinho"
NAYBINHO_CONFIG="/opt/naybinho/config"
NAYBINHO_PORT=80
NAYBINHO_API_PORT=8000
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# ── Funções de log ────────────────────────────────────────────────────────────
log()      { echo -e "${GREEN}[✓]${NC} $*"; }
info()     { echo -e "${BLUE}[i]${NC} $*"; }
warn()     { echo -e "${YELLOW}[!]${NC} $*"; }
error()    { echo -e "${RED}[✗]${NC} $*" >&2; }
header()   { echo -e "\n${BOLD}${CYAN}══════════════════════════════════════${NC}"; echo -e "${BOLD}${CYAN}  $*${NC}"; echo -e "${BOLD}${CYAN}══════════════════════════════════════${NC}"; }
die()      { error "$*"; exit 1; }

# ── Banner ────────────────────────────────────────────────────────────────────
print_banner() {
    echo -e "${CYAN}"
    cat << 'EOF'
  ███╗   ██╗ █████╗ ██╗   ██╗██████╗ ██╗███╗   ██╗██╗  ██╗ ██████╗
  ████╗  ██║██╔══██╗╚██╗ ██╔╝██╔══██╗██║████╗  ██║██║  ██║██╔═══██╗
  ██╔██╗ ██║███████║ ╚████╔╝ ██████╔╝██║██╔██╗ ██║███████║██║   ██║
  ██║╚██╗██║██╔══██║  ╚██╔╝  ██╔══██╗██║██║╚██╗██║██╔══██║██║   ██║
  ██║ ╚████║██║  ██║   ██║   ██████╔╝██║██║ ╚████║██║  ██║╚██████╔╝
  ╚═╝  ╚═══╝╚═╝  ╚═╝   ╚═╝   ╚═════╝ ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝ ╚═════╝
                         NAS — Home Lab OS
EOF
    echo -e "${NC}"
    echo -e "  Versão: ${BOLD}${NAYBINHO_VERSION}${NC}   Instalador"
    echo ""
}

# ── Verificações iniciais ─────────────────────────────────────────────────────
check_root() {
    [[ $EUID -eq 0 ]] || die "Execute como root: sudo bash install.sh"
}

check_ubuntu() {
    header "Verificando sistema operacional"
    if [[ ! -f /etc/os-release ]]; then
        die "Não foi possível detectar o SO. Ubuntu 26.04 LTS é necessário."
    fi
    source /etc/os-release
    if [[ "$ID" != "ubuntu" ]]; then
        die "SO não suportado: $PRETTY_NAME. Necessário Ubuntu 26.04 LTS."
    fi
    local version_id="$VERSION_ID"
    # Aceita 24.04, 26.04 e futuros LTS
    if [[ "$version_id" < "24.04" ]]; then
        die "Ubuntu $version_id não suportado. Mínimo: Ubuntu 24.04 LTS."
    fi
    log "SO compatível: $PRETTY_NAME"
}

check_arch() {
    local arch
    arch=$(uname -m)
    [[ "$arch" == "x86_64" ]] || warn "Arquitetura $arch não testada (esperado: x86_64)"
    log "Arquitetura: $arch"
}

check_ram() {
    local ram_mb
    ram_mb=$(awk '/MemTotal/ {print int($2/1024)}' /proc/meminfo)
    if [[ $ram_mb -lt 1024 ]]; then
        warn "RAM detectada: ${ram_mb}MB. Recomendado mínimo: 2048MB."
    else
        log "RAM: ${ram_mb}MB"
    fi
}

check_disk() {
    local disk_gb
    disk_gb=$(df -BG / | awk 'NR==2 {print int($4)}')
    if [[ $disk_gb -lt 10 ]]; then
        warn "Espaço livre em /: ${disk_gb}GB. Recomendado mínimo: 20GB."
    else
        log "Espaço livre: ${disk_gb}GB"
    fi
}

check_internet() {
    info "Verificando conectividade..."
    if ! ping -c 1 -W 5 8.8.8.8 &>/dev/null; then
        die "Sem acesso à internet. Necessário para instalar dependências."
    fi
    log "Internet: OK"
}

# ── Instalação de dependências ────────────────────────────────────────────────
install_dependencies() {
    header "Instalando dependências do sistema"

    info "Atualizando lista de pacotes..."
    apt-get update -qq

    info "Instalando pacotes essenciais..."
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl wget git vim nano \
        build-essential pkg-config \
        ca-certificates gnupg lsb-release \
        apt-transport-https software-properties-common \
        > /dev/null 2>&1
    log "Pacotes essenciais instalados"

    # Python 3
    info "Instalando Python 3..."
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        python3 python3-pip python3-venv python3-dev \
        > /dev/null 2>&1
    log "Python $(python3 --version) instalado"

    # Node.js LTS (via NodeSource)
    if ! command -v node &>/dev/null; then
        info "Instalando Node.js LTS..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | bash - > /dev/null 2>&1
        DEBIAN_FRONTEND=noninteractive apt-get install -y nodejs > /dev/null 2>&1
    fi
    log "Node.js $(node --version) instalado"

    # Nginx
    info "Instalando Nginx..."
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        nginx nginx-extras \
        > /dev/null 2>&1
    systemctl stop nginx 2>/dev/null || true
    log "Nginx instalado"

    # Docker
    if ! command -v docker &>/dev/null; then
        info "Instalando Docker..."
        install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
            gpg --dearmor -o /etc/apt/keyrings/docker.gpg
        chmod a+r /etc/apt/keyrings/docker.gpg
        echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
            > /etc/apt/sources.list.d/docker.list
        apt-get update -qq > /dev/null 2>&1
        DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
            docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin \
            > /dev/null 2>&1
        systemctl enable --now docker
    fi
    log "Docker $(docker --version | cut -d' ' -f3 | tr -d ',') instalado"

    # RAID e storage
    info "Instalando ferramentas de storage..."
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        mdadm \
        zfsutils-linux \
        lvm2 \
        parted gdisk \
        util-linux \
        e2fsprogs xfsprogs btrfs-progs \
        > /dev/null 2>&1
    log "Ferramentas de storage instaladas (mdadm, ZFS, LVM)"

    # Monitoramento de hardware
    info "Instalando ferramentas de monitoramento..."
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        smartmontools \
        hdparm \
        nvme-cli \
        lm-sensors \
        hddtemp \
        iotop \
        sysstat \
        htop \
        iftop \
        nethogs \
        > /dev/null 2>&1
    log "Ferramentas de monitoramento instaladas"

    # Compartilhamento de rede
    info "Instalando serviços de rede (Samba + NFS)..."
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        samba samba-common-bin \
        nfs-kernel-server nfs-common \
        avahi-daemon \
        > /dev/null 2>&1
    log "Samba e NFS instalados"

    # Utilitários
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        jq \
        rsync \
        rclone \
        openssl \
        sqlite3 \
        cron \
        logrotate \
        ufw \
        fail2ban \
        > /dev/null 2>&1
    log "Utilitários instalados"

    # Detectar sensores de hardware
    sensors-detect --auto > /dev/null 2>&1 || true

    log "Todas as dependências instaladas com sucesso"
}

# ── Criar usuário sistema ─────────────────────────────────────────────────────
create_user() {
    header "Criando usuário do sistema"

    if id "$NAYBINHO_USER" &>/dev/null; then
        warn "Usuário '$NAYBINHO_USER' já existe, pulando criação."
    else
        useradd --system \
            --create-home \
            --home-dir "$NAYBINHO_HOME" \
            --shell /bin/bash \
            --comment "NayBinho NAS System User" \
            --groups docker,www-data \
            "$NAYBINHO_USER"
        log "Usuário '$NAYBINHO_USER' criado"
    fi

    # Adicionar ao grupo docker se não estiver
    usermod -aG docker "$NAYBINHO_USER" 2>/dev/null || true
    log "Usuário '$NAYBINHO_USER' adicionado ao grupo docker"
}

# ── Instalar arquivos do NayBinho ─────────────────────────────────────────────
install_files() {
    header "Copiando arquivos para $NAYBINHO_HOME"

    # Criar estrutura de diretórios
    mkdir -p \
        "${NAYBINHO_HOME}"/{backend,frontend,system,config} \
        "${NAYBINHO_HOME}/system"/{services,nginx,scripts,docker} \
        "${NAYBINHO_DATA}"/{db,uploads,backups} \
        "${NAYBINHO_LOGS}" \
        /etc/naybinho

    # Copiar arquivos do projeto
    if [[ -d "$SOURCE_DIR/backend" ]]; then
        rsync -a --exclude '__pycache__' --exclude '*.pyc' \
            "${SOURCE_DIR}/backend/" "${NAYBINHO_HOME}/backend/"
        log "Backend copiado"
    else
        warn "Diretório backend não encontrado em $SOURCE_DIR"
    fi

    if [[ -d "$SOURCE_DIR/frontend/dist" ]]; then
        rsync -a "${SOURCE_DIR}/frontend/dist/" "${NAYBINHO_HOME}/frontend/dist/"
        log "Frontend (build) copiado"
    elif [[ -d "$SOURCE_DIR/frontend" ]]; then
        warn "Frontend não compilado. Compilando..."
        cd "${SOURCE_DIR}/frontend"
        npm ci --silent
        npm run build --silent
        rsync -a "${SOURCE_DIR}/frontend/dist/" "${NAYBINHO_HOME}/frontend/dist/"
        log "Frontend compilado e copiado"
    fi

    # Copiar scripts e configs do sistema
    rsync -a "${SOURCE_DIR}/system/" "${NAYBINHO_HOME}/system/"
    chmod +x "${NAYBINHO_HOME}/system/scripts/"*.sh
    log "Scripts do sistema copiados"

    # Ajustar permissões
    chown -R "${NAYBINHO_USER}:${NAYBINHO_GROUP}" "${NAYBINHO_HOME}"
    chown -R "${NAYBINHO_USER}:${NAYBINHO_GROUP}" "${NAYBINHO_DATA}"
    chown -R "${NAYBINHO_USER}:${NAYBINHO_GROUP}" "${NAYBINHO_LOGS}"
    chmod 755 "${NAYBINHO_HOME}"
    chmod 750 "${NAYBINHO_HOME}/config"
    chmod 700 "${NAYBINHO_DATA}/db"
    log "Permissões configuradas"
}

# ── Ambiente Python ───────────────────────────────────────────────────────────
setup_python_env() {
    header "Configurando ambiente Python"

    info "Criando virtualenv..."
    python3 -m venv "${NAYBINHO_HOME}/venv"
    source "${NAYBINHO_HOME}/venv/bin/activate"

    info "Instalando dependências Python..."
    pip install --upgrade pip wheel setuptools --quiet

    if [[ -f "${NAYBINHO_HOME}/backend/requirements.txt" ]]; then
        pip install -r "${NAYBINHO_HOME}/backend/requirements.txt" --quiet
        log "Dependências Python instaladas"
    else
        warn "requirements.txt não encontrado, instalando pacotes base..."
        pip install fastapi uvicorn[standard] psutil docker pySMART sqlalchemy \
            aiosqlite python-multipart python-jose[cryptography] passlib[bcrypt] \
            httpx aiofiles pydantic-settings --quiet
    fi

    chown -R "${NAYBINHO_USER}:${NAYBINHO_GROUP}" "${NAYBINHO_HOME}/venv"
    log "Ambiente Python configurado"
}

# ── Configurar banco de dados ─────────────────────────────────────────────────
init_database() {
    header "Inicializando banco de dados"
    local db_path="${NAYBINHO_DATA}/db/naybinho.db"

    if [[ ! -f "$db_path" ]]; then
        sudo -u "$NAYBINHO_USER" \
            "${NAYBINHO_HOME}/venv/bin/python3" \
            -c "
import sys; sys.path.insert(0, '${NAYBINHO_HOME}/backend')
try:
    from database import init_db
    import asyncio
    asyncio.run(init_db())
    print('Banco de dados inicializado')
except Exception as e:
    print(f'Aviso: {e}')
" 2>/dev/null || true
        log "Banco de dados inicializado em $db_path"
    else
        log "Banco de dados já existe"
    fi
}

# ── Configurar serviços systemd ───────────────────────────────────────────────
configure_services() {
    header "Configurando serviços systemd"

    local services_src="${NAYBINHO_HOME}/system/services"
    local systemd_dir="/etc/systemd/system"

    for unit_file in \
        naybinho-backend.service \
        naybinho-frontend.service \
        naybinho-monitor.service \
        naybinho-update.service \
        naybinho-update.timer; do

        if [[ -f "${services_src}/${unit_file}" ]]; then
            cp "${services_src}/${unit_file}" "${systemd_dir}/${unit_file}"
            log "Serviço ${unit_file} instalado"
        else
            warn "Arquivo ${unit_file} não encontrado em ${services_src}"
        fi
    done

    systemctl daemon-reload

    # Habilitar serviços
    systemctl enable naybinho-backend.service
    systemctl enable naybinho-monitor.service
    systemctl enable naybinho-update.timer
    # naybinho-frontend é gerenciado pelo nginx
    log "Serviços habilitados para iniciar com o sistema"
}

# ── Configurar Nginx ──────────────────────────────────────────────────────────
configure_nginx() {
    header "Configurando Nginx"

    local nginx_conf="${NAYBINHO_HOME}/system/nginx/naybinho.conf"

    # Remover configuração padrão do nginx
    rm -f /etc/nginx/sites-enabled/default
    rm -f /etc/nginx/conf.d/default.conf

    # Instalar configuração do NayBinho
    if [[ -f "$nginx_conf" ]]; then
        cp "$nginx_conf" /etc/nginx/conf.d/naybinho.conf
        log "Configuração nginx instalada"
    fi

    # Criar diretório de cache
    mkdir -p /var/cache/nginx/naybinho
    chown www-data:www-data /var/cache/nginx/naybinho

    # Testar configuração
    if nginx -t &>/dev/null; then
        log "Configuração nginx válida"
        systemctl enable nginx
    else
        error "Configuração nginx inválida:"
        nginx -t
    fi
}

# ── Configurar Firewall ───────────────────────────────────────────────────────
configure_firewall() {
    header "Configurando Firewall (UFW)"

    ufw --force reset > /dev/null 2>&1

    ufw default deny incoming > /dev/null 2>&1
    ufw default allow outgoing > /dev/null 2>&1

    ufw allow ssh > /dev/null 2>&1
    ufw allow 80/tcp > /dev/null 2>&1    # HTTP
    ufw allow 443/tcp > /dev/null 2>&1   # HTTPS
    ufw allow 445/tcp > /dev/null 2>&1   # Samba
    ufw allow 2049/tcp > /dev/null 2>&1  # NFS
    ufw allow 2049/udp > /dev/null 2>&1

    ufw --force enable > /dev/null 2>&1
    log "Firewall configurado"
}

# ── Criar configuração inicial ────────────────────────────────────────────────
create_initial_config() {
    header "Criando configuração inicial"

    local conf_file="${NAYBINHO_CONFIG}/naybinho.conf"

    if [[ ! -f "$conf_file" ]]; then
        # Copiar config template se existir
        if [[ -f "${NAYBINHO_HOME}/system/config/naybinho.conf" ]]; then
            cp "${NAYBINHO_HOME}/system/config/naybinho.conf" "$conf_file"
        fi
    fi

    # Gerar secret key
    local secret_key
    secret_key=$(openssl rand -hex 32)

    # Criar arquivo de ambiente
    cat > "${NAYBINHO_CONFIG}/naybinho.env" <<EOF
# NayBinho NAS - Variáveis de Ambiente
# Gerado em: $(date -u +"%Y-%m-%dT%H:%M:%SZ")
NAYBINHO_SECRET_KEY=${secret_key}
NAYBINHO_ENV=production
NAYBINHO_DATA_DIR=${NAYBINHO_DATA}
NAYBINHO_LOG_DIR=${NAYBINHO_LOGS}
NAYBINHO_DB_PATH=${NAYBINHO_DATA}/db/naybinho.db
NAYBINHO_PORT=${NAYBINHO_PORT}
NAYBINHO_API_PORT=${NAYBINHO_API_PORT}
EOF

    chmod 600 "${NAYBINHO_CONFIG}/naybinho.env"
    chown "${NAYBINHO_USER}:${NAYBINHO_GROUP}" "${NAYBINHO_CONFIG}/naybinho.env"
    log "Configuração inicial criada"
}

# ── Configurar logrotate ──────────────────────────────────────────────────────
configure_logrotate() {
    cat > /etc/logrotate.d/naybinho <<EOF
${NAYBINHO_LOGS}/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 640 ${NAYBINHO_USER} ${NAYBINHO_GROUP}
    sharedscripts
    postrotate
        systemctl reload naybinho-backend 2>/dev/null || true
    endscript
}
EOF
    log "Logrotate configurado"
}

# ── Iniciar serviços ──────────────────────────────────────────────────────────
start_services() {
    header "Iniciando serviços"

    systemctl start naybinho-backend.service && log "Backend iniciado" || warn "Backend falhou ao iniciar"

    sleep 3

    systemctl start nginx && log "Nginx (frontend) iniciado" || warn "Nginx falhou ao iniciar"
    systemctl start naybinho-monitor.service && log "Monitor iniciado" || warn "Monitor falhou ao iniciar"
    systemctl start naybinho-update.timer && log "Timer de atualização iniciado" || true
}

# ── Detectar IP de acesso ─────────────────────────────────────────────────────
get_access_ip() {
    local ip
    ip=$(hostname -I | awk '{print $1}')
    echo "$ip"
}

# ── Mensagem final ────────────────────────────────────────────────────────────
print_success() {
    local ip
    ip=$(get_access_ip)

    echo ""
    echo -e "${GREEN}${BOLD}"
    echo "  ╔══════════════════════════════════════════════════════╗"
    echo "  ║          NayBinho NAS instalado com sucesso!         ║"
    echo "  ╠══════════════════════════════════════════════════════╣"
    echo -e "  ║  🌐 Interface Web:  ${CYAN}http://${ip}${GREEN}                  ║"
    echo -e "  ║  🔧 API Backend:    ${CYAN}http://${ip}:${NAYBINHO_API_PORT}/api${GREEN}         ║"
    echo -e "  ║  📖 Documentação:   ${CYAN}http://${ip}/docs${GREEN}              ║"
    echo "  ╠══════════════════════════════════════════════════════╣"
    echo "  ║  Usuário padrão: admin                               ║"
    echo "  ║  Senha padrão:   naybinho123 (TROQUE IMEDIATAMENTE!) ║"
    echo "  ╠══════════════════════════════════════════════════════╣"
    echo "  ║  Logs: journalctl -u naybinho-backend -f             ║"
    echo "  ║  Status: systemctl status naybinho-*                 ║"
    echo "  ╚══════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# ── Main ──────────────────────────────────────────────────────────────────────
main() {
    print_banner

    header "Iniciando instalação do NayBinho NAS v${NAYBINHO_VERSION}"
    echo -e "  ${YELLOW}Este processo pode levar alguns minutos...${NC}"

    check_root
    check_ubuntu
    check_arch
    check_ram
    check_disk
    check_internet

    install_dependencies
    create_user
    install_files
    setup_python_env
    init_database
    configure_services
    configure_nginx
    configure_firewall
    create_initial_config
    configure_logrotate
    start_services

    print_success
}

main "$@"
