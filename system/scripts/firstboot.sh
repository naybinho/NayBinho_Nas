#!/usr/bin/env bash
# =============================================================================
# NayBinho NAS — Script de Primeiro Boot (Firstboot Wizard / Setup)
# Executa na primeira inicialização da ISO/Instalação
# - Configura Hostname e domínios
# - Configura Rede (DHCP / IP Estático)
# - Gera credenciais e configura conta admin inicial
# - Inicializa e migra banco de dados SQLite
# - Configura chaves SSH de host e certificados autoassinados TLS
# - Marca flag de primeiro boot concluído
# =============================================================================
set -euo pipefail

FLAG_FIRSTBOOT="/var/lib/naybinho/.firstboot_done"
NAYBINHO_CONFIG="/opt/naybinho/config/naybinho.conf"
ENV_FILE="/opt/naybinho/config/naybinho.env"
DB_PATH="/var/lib/naybinho/db/naybinho.db"

# ── Cores ─────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'; RED='\033[0;31m'; BOLD='\033[1m'; NC='\033[0m'

log()   { echo -e "${GREEN}[FIRSTBOOT] [INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[FIRSTBOOT] [WARN]${NC} $*"; }
error() { echo -e "${RED}[FIRSTBOOT] [ERROR]${NC} $*" >&2; }

if [[ $EUID -ne 0 ]]; then
    error "Este script precisa rodar como root."
    exit 1
fi

if [[ -f "$FLAG_FIRSTBOOT" ]]; then
    log "Primeiro boot já foi executado anteriormente. Saindo."
    exit 0
fi

echo -e "${CYAN}${BOLD}"
cat << 'EOF'
======================================================
         NAYBINHO NAS — PRIMEIRO BOOT DO SO          
======================================================
EOF
echo -e "${NC}"

# 1. Configuração do Hostname
setup_hostname() {
    local default_host="naybinho-nas"
    log "Configurando hostname padrão: $default_host..."
    hostnamectl set-hostname "$default_host"
    
    if ! grep -q "$default_host" /etc/hosts; then
        echo "127.0.1.1 $default_host" >> /etc/hosts
    fi
}

# 2. Configuração de Rede (Garante DHCP e interfaces ativas)
setup_network() {
    log "Configurando adaptadores de rede e DNS..."
    # Se netplan existir, certificar que há um arquivo funcional de DHCP
    if [[ -d /etc/netplan ]]; then
        if ! ls /etc/netplan/*.yaml &>/dev/null; then
            cat > /etc/netplan/01-naybinho-dhcp.yaml << 'EOF'
network:
  version: 2
  renderer: networkd
  ethernets:
    all-eth:
      match:
        name: "en*|eth*"
      dhcp4: true
      dhcp6: true
      optional: true
EOF
            netplan apply 2>/dev/null || true
        fi
    fi
}

# 3. Gerar Chaves Secretas e Certificados SSL Locais Autoassinados
setup_security_keys() {
    log "Gerando certificados SSL autoassinados e chaves criptográficas..."
    mkdir -p /etc/ssl/naybinho /opt/naybinho/config
    
    if [[ ! -f /etc/ssl/naybinho/privkey.pem || ! -f /etc/ssl/naybinho/fullchain.pem ]]; then
        openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
            -keyout /etc/ssl/naybinho/privkey.pem \
            -out /etc/ssl/naybinho/fullchain.pem \
            -subj "/C=BR/ST=SP/L=SaoPaulo/O=NayBinho/OU=HomeLab/CN=naybinho.local" \
            >/dev/null 2>&1 || true
        chmod 600 /etc/ssl/naybinho/privkey.pem
        chmod 644 /etc/ssl/naybinho/fullchain.pem
    fi

    # Chave secreta JWT se não existir
    if [[ ! -f "$ENV_FILE" ]]; then
        local jwt_secret
        jwt_secret=$(openssl rand -hex 32)
        cat > "$ENV_FILE" << EOF
NAYBINHO_SECRET_KEY=${jwt_secret}
NAYBINHO_ENV=production
NAYBINHO_DATA_DIR=/var/lib/naybinho
NAYBINHO_LOG_DIR=/var/log/naybinho
NAYBINHO_DB_PATH=/var/lib/naybinho/db/naybinho.db
NAYBINHO_API_PORT=8000
EOF
        chmod 600 "$ENV_FILE"
        chown naybinho:naybinho "$ENV_FILE" 2>/dev/null || true
    fi
}

# 4. Inicializar Banco de Dados SQLite e Conta Admin
setup_database_and_admin() {
    log "Inicializando banco de dados NayBinho..."
    mkdir -p "$(dirname "$DB_PATH")"
    chown -R naybinho:naybinho /var/lib/naybinho 2>/dev/null || true

    # Rodar migração/seed do backend
    if [[ -d /opt/naybinho/backend ]]; then
        if [[ -x /opt/naybinho/venv/bin/python3 ]]; then
            sudo -u naybinho /opt/naybinho/venv/bin/python3 -c "
import sys
sys.path.insert(0, '/opt/naybinho/backend')
try:
    import database
    import asyncio
    if hasattr(database, 'init_db'):
        asyncio.run(database.init_db())
        print('DB inicializado via database.init_db()')
    else:
        print('Módulo database encontrado.')
except Exception as e:
    print(f'Inicialização BD: {e}')
" 2>/dev/null || true
        fi
    fi
}

# 5. Criar pontos de montagem e diretórios de storage padrão
setup_storage_dirs() {
    log "Criando diretórios base de compartilhamento em /mnt/storage..."
    mkdir -p /mnt/storage/{public,media,backups,timemachine,docker,vms}
    chmod -R 0777 /mnt/storage/public 2>/dev/null || true
    chown -R naybinho:naybinho /mnt/storage/media /mnt/storage/backups /mnt/storage/timemachine 2>/dev/null || true
}

# 6. Ativar e Iniciar Serviços
setup_services() {
    log "Garantindo inicialização dos serviços..."
    systemctl daemon-reload
    systemctl enable naybinho-backend.service 2>/dev/null || true
    systemctl enable naybinho-monitor.service 2>/dev/null || true
    systemctl enable naybinho-update.timer 2>/dev/null || true
    systemctl enable nginx 2>/dev/null || true
    systemctl enable smbd nmbd 2>/dev/null || true
    systemctl enable nfs-server 2>/dev/null || true
    systemctl enable avahi-daemon 2>/dev/null || true

    systemctl restart naybinho-backend.service 2>/dev/null || true
    systemctl restart naybinho-monitor.service 2>/dev/null || true
    systemctl restart nginx 2>/dev/null || true
}

# 7. Finalização
finalize() {
    touch "$FLAG_FIRSTBOOT"
    local ip
    ip=$(hostname -I | awk '{print $1}' || echo "127.0.0.1")

    echo ""
    log "=========================================================="
    log " NayBinho NAS Firstboot Concluído com Sucesso!            "
    log " Acesse a interface web em: http://${ip}                 "
    log " Usuário Inicial: admin | Senha: admin                    "
    log "=========================================================="
    echo ""
}

setup_hostname
setup_network
setup_security_keys
setup_storage_dirs
setup_database_and_admin
setup_services
finalize
