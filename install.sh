#!/usr/bin/env bash
# =============================================================================
# NayBinho NAS — Instalador Oficial de 1 Linha
# =============================================================================
# Como usar:
#   curl -fsSL https://raw.githubusercontent.com/naybinho/NayBinho_Nas/main/install.sh | sudo bash
# =============================================================================
set -euo pipefail

# Cores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

clear || true

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
echo -e "${BOLD}Bem-vindo ao instalador simplificado do NayBinho NAS!${NC}"
echo -e "Este script transformará seu computador em um servidor Home Lab completo."
echo -e "------------------------------------------------------------------"

# 1. Checagem de Root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}[ERRO] Este script precisa ser executado como root.${NC}"
    echo -e "Por favor, execute: ${BOLD}sudo bash install.sh${NC}"
    exit 1
fi

# 2. Obter IP local da máquina
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")

echo -e "\n${BLUE}>> [1/5] Atualizando repositórios e instalando dependências...${NC}"
apt-get update -qq
DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    curl wget git rsync tar unzip jq \
    python3 python3-pip python3-venv \
    nginx redis-server mdadm smartmontools \
    ca-certificates gnupg lsb-release ufw >/dev/null 2>&1

echo -e "${GREEN}✓ Dependências essenciais instaladas com sucesso.${NC}"

# 3. Instalar Docker se ausente
echo -e "\n${BLUE}>> [2/5] Verificando Docker Engine...${NC}"
if ! command -v docker &>/dev/null; then
    echo -e "   Instalando Docker Engine nativo oficial..."
    curl -fsSL https://get.docker.com | sh >/dev/null 2>&1
    systemctl enable --now docker >/dev/null 2>&1
fi
echo -e "${GREEN}✓ Docker Engine pronto e ativo.${NC}"

# 4. Criar diretórios de instalação
echo -e "\n${BLUE}>> [3/5] Configurando ambiente do NayBinho NAS...${NC}"
INSTALL_DIR="/opt/naybinho"
mkdir -p "${INSTALL_DIR}"
mkdir -p "${INSTALL_DIR}/data"
mkdir -p "${INSTALL_DIR}/logs"
mkdir -p "/etc/naybinho"

# Download ou cópia do pacote mais recente
TEMP_DIR=$(mktemp -d)
cd "${TEMP_DIR}"

if [[ -f "/cdrom/dist-release/naybinho-update-v1.0.0.tar.gz" ]]; then
    # Instalando a partir de CD/pendrive local
    echo -e "   Instalando a partir da mídia local..."
    tar -xzf "/cdrom/dist-release/naybinho-update-v1.0.0.tar.gz" -C "${INSTALL_DIR}"
elif [[ -d "/opt/naybinho/backend" ]]; then
    echo -e "   Arquivos já presentes em /opt/naybinho."
else
    echo -e "   Baixando versão oficial mais recente do GitHub..."
    LATEST_TAR="https://github.com/naybinho/NayBinho_Nas/releases/latest/download/naybinho-update-v1.0.0.tar.gz"
    if wget -q --spider "${LATEST_TAR}" 2>/dev/null; then
        wget -q "${LATEST_TAR}" -O update.tar.gz
        tar -xzf update.tar.gz -C "${INSTALL_DIR}"
    else
        # Fallback para clone do git
        git clone --depth 1 https://github.com/naybinho/NayBinho_Nas.git repo
        cp -r repo/backend "${INSTALL_DIR}/"
        cp -r repo/appstore "${INSTALL_DIR}/"
        cp -r repo/system "${INSTALL_DIR}/"
        cp repo/VERSION "${INSTALL_DIR}/" 2>/dev/null || echo "1.0.0" > "${INSTALL_DIR}/VERSION"
    fi
fi
rm -rf "${TEMP_DIR}"

# 5. Criar Virtualenv Python e instalar dependências do Backend
echo -e "\n${BLUE}>> [4/5] Configurando serviços do sistema e API...${NC}"
python3 -m venv "${INSTALL_DIR}/venv"
"${INSTALL_DIR}/venv/bin/pip" install --upgrade pip -q
if [[ -f "${INSTALL_DIR}/backend/requirements.txt" ]]; then
    "${INSTALL_DIR}/venv/bin/pip" install -r "${INSTALL_DIR}/backend/requirements.txt" -q
else
    "${INSTALL_DIR}/venv/bin/pip" install fastapi uvicorn pydantic pydantic-settings python-jose passlib bcrypt psutil docker aiofiles -q
fi

# Configurar Systemd Service para o Backend
cat << EOF > /etc/systemd/system/naybinho.service
[Unit]
Description=NayBinho NAS Server & Dashboard API
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=root
WorkingDirectory=${INSTALL_DIR}/backend
ExecStart=${INSTALL_DIR}/venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3
Environment=NAYBINHO_ENV=production

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now naybinho.service >/dev/null 2>&1

# Liberar portas no firewall se ativo
if command -v ufw &>/dev/null; then
    ufw allow 8000/tcp >/dev/null 2>&1 || true
    ufw allow 80/tcp >/dev/null 2>&1 || true
    ufw allow 445/tcp >/dev/null 2>&1 || true
fi

echo -e "${GREEN}✓ Serviços configurados e iniciados com sucesso!${NC}"

# 6. Finalização Amigável
echo -e "\n${BLUE}>> [5/5] Finalizando instalação...${NC}"
sleep 2

clear || true
echo -e "${GREEN}"
echo -e "╔════════════════════════════════════════════════════════════════════════╗"
echo -e "║                                                                        ║"
echo -e "║                 🎉 NAYBINHO NAS INSTALADO COM SUCESSO!                 ║"
echo -e "║                                                                        ║"
echo -e "╠════════════════════════════════════════════════════════════════════════╣"
echo -e "║                                                                        ║"
echo -e "║  Abra seu navegador em qualquer computador ou celular na mesma rede:   ║"
echo -e "║                                                                        ║"
echo -e "║  👉 ${BOLD}http://${LOCAL_IP}:8000${NC}${GREEN}                                             ║"
echo -e "║  👉 ${BOLD}http://naybinho-nas.local:8000${NC}${GREEN}                                       ║"
echo -e "║                                                                        ║"
echo -e "║  Credenciais padrão:                                                   ║"
echo -e "║  • Usuário: ${BOLD}admin${NC}${GREEN}                                                      ║"
echo -e "║  • Senha inicial: ${BOLD}naybinho${NC}${GREEN}                                             ║"
echo -e "║                                                                        ║"
echo -e "║  Aproveite seu Home Lab com Docker nativo e proteção RAID!             ║"
echo -e "╚════════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}\n"
