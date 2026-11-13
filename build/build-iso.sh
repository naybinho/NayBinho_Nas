#!/usr/bin/env bash
# =============================================================================
# build-iso.sh — NayBinho NAS ISO Builder
# =============================================================================
# Gera a ISO customizada do NayBinho NAS baseada em Ubuntu 26.04.1 LTS.
#
# Uso:
#   sudo bash build-iso.sh [opções]
#
# Opções:
#   --version <ver>   Versão da ISO (padrão: 1.0.0)
#   --arch <arch>     Arquitetura: amd64 | arm64 (padrão: amd64)
#   --output <dir>    Diretório de saída (padrão: ./output)
#   --clean           Limpa o ambiente de build antes de começar
#   --no-download     Não baixar Ubuntu base se já existir em cache
#   --help            Exibe esta ajuda
#
# Pré-requisitos (instalados automaticamente se ausentes):
#   live-build, squashfs-tools, genisoimage / xorriso,
#   debootstrap, isolinux/syslinux, grub-efi-amd64-bin
#
# Resultado:
#   output/naybinho-nas-<version>-<arch>.iso
# =============================================================================

set -euo pipefail

# ---------------------------------------------------------------------------
# Configurações padrão
# ---------------------------------------------------------------------------
NAYBINHO_VERSION="${NAYBINHO_VERSION:-1.0.0}"
NAYBINHO_VERSION="${NAYBINHO_VERSION#v}"
ARCH="${ARCH:-amd64}"
UBUNTU_CODENAME="noble"           # Ubuntu LTS base
UBUNTU_VERSION="24.04.5"
UBUNTU_BASE_URL="https://releases.ubuntu.com/noble"
UBUNTU_ISO_NAME="ubuntu-${UBUNTU_VERSION}-live-server-${ARCH}.iso"
OUTPUT_DIR="${OUTPUT_DIR:-$(pwd)/dist-release}"
CACHE_DIR="$(pwd)/.build-cache"
BUILD_DIR="/tmp/build-work"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLEAN_BUILD=false
NO_DOWNLOAD=false
mkdir -p "${OUTPUT_DIR}" "${CACHE_DIR}"
LOG_FILE="${OUTPUT_DIR}/build-$(date +%Y%m%d-%H%M%S).log"
ISO_LABEL="NayBinhoNAS"
ISO_OUTPUT_NAME="naybinho-nas-v${NAYBINHO_VERSION}-${ARCH}.iso"

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ---------------------------------------------------------------------------
# Funções utilitárias
# ---------------------------------------------------------------------------

log() { echo -e "${CYAN}[$(date '+%H:%M:%S')]${NC} $*" | tee -a "${LOG_FILE}"; }
info() { echo -e "${GREEN}[INFO]${NC} $*" | tee -a "${LOG_FILE}"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $*" | tee -a "${LOG_FILE}"; }
error() { echo -e "${RED}[ERROR]${NC} $*" | tee -a "${LOG_FILE}"; }
step() { echo -e "\n${BOLD}${BLUE}══════════════════════════════════════════════${NC}" | tee -a "${LOG_FILE}"
         echo -e "${BOLD}${BLUE}  $*${NC}" | tee -a "${LOG_FILE}"
         echo -e "${BOLD}${BLUE}══════════════════════════════════════════════${NC}" | tee -a "${LOG_FILE}"; }
die() { error "$*"; exit 1; }

usage() {
    cat <<EOF
NayBinho NAS ISO Builder v${NAYBINHO_VERSION}

Uso: sudo bash build-iso.sh [opções]

Opções:
  --version <ver>   Versão da ISO        (padrão: ${NAYBINHO_VERSION})
  --arch <arch>     amd64 | arm64        (padrão: ${ARCH})
  --output <dir>    Diretório de saída   (padrão: ./output)
  --clean           Limpa build anterior antes de começar
  --no-download     Reutiliza o ISO Ubuntu em cache (se existir)
  --help            Exibe esta mensagem

Exemplo:
  sudo bash build-iso.sh --version 1.0.0 --arch amd64 --output /tmp/naybinho

EOF
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        die "Este script deve ser executado como root (use: sudo bash build-iso.sh)"
    fi
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --version) NAYBINHO_VERSION="${2#v}"; shift 2 ;;
            --arch) ARCH="$2"; shift 2 ;;
            --output) OUTPUT_DIR="$2"; shift 2 ;;
            --clean) CLEAN_BUILD=true; shift ;;
            --no-download) NO_DOWNLOAD=true; shift ;;
            --help|-h) usage; exit 0 ;;
            *) die "Opção desconhecida: $1. Use --help para ajuda." ;;
        esac
    done
    mkdir -p "${OUTPUT_DIR}"
    ISO_OUTPUT_NAME="naybinho-nas-v${NAYBINHO_VERSION}-${ARCH}.iso"
}

check_disk_space() {
    local available_gb
    available_gb=$(df -BG /tmp 2>/dev/null | awk 'NR==2{print $4}' | tr -d 'G' || echo "50")
    info "Espaço em disco em /tmp: ${available_gb}GB disponível (OK)"
}

# ---------------------------------------------------------------------------
# Passo 1 — Verificar e instalar dependências
# ---------------------------------------------------------------------------
install_dependencies() {
    step "Verificando e instalando dependências"

    local packages=(
        live-build
        squashfs-tools
        xorriso
        isolinux
        syslinux-utils
        debootstrap
        grub-efi-amd64-bin
        grub-pc-bin
        mtools
        dosfstools
        gawk
        rsync
        wget
        curl
        jq
        git
        apt-utils
        gnupg2
        ca-certificates
    )

    info "Atualizando lista de pacotes..."
    apt-get update -qq

    info "Instalando dependências de build..."
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${packages[@]}"

    info "Dependências instaladas com sucesso."
}

# ---------------------------------------------------------------------------
# Passo 2 — Preparar diretórios
# ---------------------------------------------------------------------------
prepare_dirs() {
    step "Preparando diretórios de trabalho"

    if [[ "${CLEAN_BUILD}" == "true" ]]; then
        warn "Limpando build anterior..."
        rm -rf "${BUILD_DIR}"
    fi

    mkdir -p "${OUTPUT_DIR}"
    mkdir -p "${CACHE_DIR}"
    mkdir -p "${BUILD_DIR}"
    mkdir -p "${LOG_FILE%/*}"
    touch "${LOG_FILE}"

    info "Diretórios prontos:"
    info "  Build:  ${BUILD_DIR}"
    info "  Cache:  ${CACHE_DIR}"
    info "  Output: ${OUTPUT_DIR}"
}

# ---------------------------------------------------------------------------
# Passo 3 — Baixar ISO Ubuntu base
# ---------------------------------------------------------------------------
download_ubuntu_iso() {
    step "Obtendo Ubuntu ${UBUNTU_VERSION} LTS base"

    local iso_cache="${CACHE_DIR}/${UBUNTU_ISO_NAME}"
    local checksum_url="${UBUNTU_BASE_URL}/SHA256SUMS"
    local checksum_cache="${CACHE_DIR}/SHA256SUMS"

    if [[ "${NO_DOWNLOAD}" == "true" ]] && [[ -f "${iso_cache}" ]]; then
        info "Reutilizando ISO em cache: ${iso_cache}"
        return 0
    fi

    if [[ ! -f "${iso_cache}" ]]; then
        info "Baixando Ubuntu ${UBUNTU_VERSION} LTS (${ARCH})..."
        info "URL: ${UBUNTU_BASE_URL}/${UBUNTU_ISO_NAME}"
        wget -c --progress=bar:force \
            "${UBUNTU_BASE_URL}/${UBUNTU_ISO_NAME}" \
            -O "${iso_cache}" 2>&1 | tee -a "${LOG_FILE}"
    else
        info "ISO encontrada em cache: ${iso_cache}"
    fi

    info "Baixando checksums para verificação..."
    wget -q "${checksum_url}" -O "${checksum_cache}"

    info "Verificando integridade da ISO..."
    local expected_hash
    expected_hash=$(grep "${UBUNTU_ISO_NAME}" "${checksum_cache}" | awk '{print $1}')

    if [[ -z "${expected_hash}" ]]; then
        warn "Não foi possível verificar o checksum (arquivo não encontrado nos checksums)."
    else
        local actual_hash
        actual_hash=$(sha256sum "${iso_cache}" | awk '{print $1}')
        if [[ "${actual_hash}" == "${expected_hash}" ]]; then
            info "✅ Checksum verificado com sucesso."
        else
            die "❌ Checksum inválido! ISO pode estar corrompida. Delete ${iso_cache} e tente novamente."
        fi
    fi
}

# ---------------------------------------------------------------------------
# Passo 4 — Extrair e preparar sistema de arquivos
# ---------------------------------------------------------------------------
prepare_filesystem() {
    step "Extraindo e preparando sistema de arquivos"

    local iso_cache="${CACHE_DIR}/${UBUNTU_ISO_NAME}"
    local extract_dir="${BUILD_DIR}/iso-extract"
    local squash_dir="${BUILD_DIR}/squashfs-root"

    mkdir -p "${extract_dir}" "${squash_dir}"

    info "Extraindo conteúdo da ISO original com xorriso..."
    xorriso -osirrox on -indev "${iso_cache}" -extract / "${extract_dir}" 2>&1 | tee -a "${LOG_FILE}"
    chmod -R u+w "${extract_dir}"

    # Identificar o squashfs principal do Ubuntu (ubuntu-server-minimal ou filesystem.squashfs)
    TARGET_SQUASH=""
    for candidate in \
        "${extract_dir}/casper/ubuntu-server-minimal.squashfs" \
        "${extract_dir}/casper/filesystem.squashfs" \
        "${extract_dir}/casper/minimal.squashfs"; do
        if [[ -f "${candidate}" ]]; then
            TARGET_SQUASH="${candidate}"
            break
        fi
    done
    if [[ -z "${TARGET_SQUASH}" ]]; then
        TARGET_SQUASH=$(find "${extract_dir}/casper" -name "*.squashfs" 2>/dev/null | head -n 1)
    fi

    if [[ -z "${TARGET_SQUASH}" || ! -f "${TARGET_SQUASH}" ]]; then
        die "Nenhum arquivo squashfs encontrado em ${extract_dir}/casper"
    fi

    TARGET_SQUASH_NAME="$(basename "${TARGET_SQUASH}")"
    info "Squashfs identificado: ${TARGET_SQUASH_NAME}"

    info "Extraindo sistema de arquivos (${TARGET_SQUASH_NAME})..."
    unsquashfs -f -d "${squash_dir}" "${TARGET_SQUASH}"

    info "Removendo pacotes offline para manter a ISO compacta e compatível..."
    rm -rf "${extract_dir}/pool" "${extract_dir}/dists" 2>/dev/null || true

    info "Sistema de arquivos extraído em: ${squash_dir}"
}

# ---------------------------------------------------------------------------
# Passo 5 — Customizar o sistema de arquivos (chroot)
# ---------------------------------------------------------------------------
customize_filesystem() {
    step "Customizando sistema de arquivos NayBinho"

    local squash_dir="${BUILD_DIR}/squashfs-root"

    # Montar filesystems necessários para chroot
    info "Preparando ambiente chroot..."
    mount --bind /dev     "${squash_dir}/dev"
    mount --bind /dev/pts "${squash_dir}/dev/pts"
    mount --bind /proc    "${squash_dir}/proc"
    mount --bind /sys     "${squash_dir}/sys"
    mount --bind /run     "${squash_dir}/run"

    # DNS para o chroot
    rm -f "${squash_dir}/etc/resolv.conf" 2>/dev/null || true
    echo "nameserver 1.1.1.1" > "${squash_dir}/etc/resolv.conf"
    echo "nameserver 8.8.8.8" >> "${squash_dir}/etc/resolv.conf"

    # Habilitar repositórios universe e multiverse
    if [[ -f "${squash_dir}/etc/apt/sources.list.d/ubuntu.sources" ]]; then
        sed -i 's/Components: main/Components: main universe restricted multiverse/' "${squash_dir}/etc/apt/sources.list.d/ubuntu.sources" 2>/dev/null || true
    fi
    if [[ -f "${squash_dir}/etc/apt/sources.list" ]]; then
        sed -i 's/main/main universe restricted multiverse/' "${squash_dir}/etc/apt/sources.list" 2>/dev/null || true
    fi

    # Função para executar comandos no chroot
    chroot_exec() {
        chroot "${squash_dir}" /bin/bash -c "$*" 2>&1 | tee -a "${LOG_FILE}"
    }

    # --- Atualizar sistema base ---
    info "Atualizando sistema base..."
    chroot_exec "apt-get update -qq"

    # --- Instalar pacotes NayBinho ---
    info "Instalando pacotes NayBinho NAS..."
    chroot_exec "DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        $(grep -v '^#' "${SCRIPT_DIR}/packages.list" | grep -v '^$' | tr '\n' ' ') || true"

    # --- Instalar Docker Engine ---
    info "Instalando Docker Engine..."
    chroot_exec "
        install -m 0755 -d /etc/apt/keyrings
        curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
        chmod a+r /etc/apt/keyrings/docker.asc
        echo 'deb [arch=amd64 signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu ${UBUNTU_CODENAME} stable' \
            > /etc/apt/sources.list.d/docker.list
        apt-get update -qq
        DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
            docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    "

    # --- Configurar hostname e identidade completa ---
    info "Configurando identidade do sistema (NayBinho NAS)..."
    echo "naybinho-nas" > "${squash_dir}/etc/hostname"
    cat > "${squash_dir}/etc/hosts" <<EOF
127.0.0.1   localhost
127.0.1.1   naybinho-nas naybinho-nas.local
::1         localhost ip6-localhost ip6-loopback
ff02::1     ip6-allnodes
ff02::2     ip6-allrouters
EOF

    # Substituir metadados e branding do Ubuntu por NayBinho NAS
    info "Aplicando identidade oficial NayBinho NAS em os-release e issue..."
    cat > "${squash_dir}/etc/os-release" <<'EOF'
NAME="NayBinho NAS"
VERSION="1.0.0 (Noble Numbat)"
ID=naybinho
ID_LIKE=ubuntu
PRETTY_NAME="NayBinho NAS v1.0.0"
VERSION_ID="1.0.0"
HOME_URL="https://naybinho.io"
SUPPORT_URL="https://naybinho.io/support"
BUG_REPORT_URL="https://naybinho.io/bugs"
PRIVACY_POLICY_URL="https://naybinho.io/privacy"
UBUNTU_CODENAME=noble
EOF
    cp "${squash_dir}/etc/os-release" "${squash_dir}/usr/lib/os-release" 2>/dev/null || true

    cat > "${squash_dir}/etc/lsb-release" <<'EOF'
DISTRIB_ID=NayBinhoNAS
DISTRIB_RELEASE=1.0.0
DISTRIB_CODENAME=noble
DISTRIB_DESCRIPTION="NayBinho NAS v1.0.0"
EOF

    echo "NayBinho NAS v1.0.0 \n \l" > "${squash_dir}/etc/issue"
    echo "NayBinho NAS v1.0.0" > "${squash_dir}/etc/issue.net"

    # --- Copiar arquivos do NayBinho ---
    info "Copiando arquivos do NayBinho NAS..."
    mkdir -p "${squash_dir}/opt/naybinho"
    rsync -a --exclude='.git' --exclude='node_modules' --exclude='__pycache__' \
        "${SCRIPT_DIR}/../backend" \
        "${SCRIPT_DIR}/../frontend/dist" \
        "${SCRIPT_DIR}/../system" \
        "${SCRIPT_DIR}/../appstore" \
        "${SCRIPT_DIR}/../VERSION" \
        "${squash_dir}/opt/naybinho/" || true

    # Garantir permissão de execução nos scripts
    chmod +x "${squash_dir}/opt/naybinho/system/scripts/"*.sh 2>/dev/null || true

    # --- Criar usuário naybinho ---
    info "Criando usuário do sistema naybinho..."
    chroot_exec "
        useradd -r -s /usr/sbin/nologin -d /opt/naybinho -c 'NayBinho NAS System' naybinho 2>/dev/null || true
        usermod -aG docker naybinho 2>/dev/null || true
    "

    # --- Configurar Instalador TUI NayBinho no tty1 (Live ISO) ---
    info "Configurando Instalador TUI NayBinho NAS..."
    cat > "${squash_dir}/etc/systemd/system/naybinho-installer.service" <<'UNITEOF'
[Unit]
Description=NayBinho NAS Interactive TUI Installer
After=network.target getty.target
Conflicts=getty@tty1.service
Before=getty@tty1.service

[Service]
Type=idle
ExecStart=/opt/naybinho/system/scripts/wizard-install.sh
StandardInput=tty-force
StandardOutput=inherit
StandardError=inherit
TTYPath=/dev/tty1
TTYReset=yes
TTYVHangup=yes
Restart=no

[Install]
WantedBy=multi-user.target
UNITEOF

    # --- Instalar e configurar serviços systemd ---
    info "Configurando serviços systemd..."

    cat > "${squash_dir}/etc/systemd/system/naybinho-backend.service" <<'UNITEOF'
[Unit]
Description=NayBinho NAS Backend API
After=network-online.target docker.service redis.service
Wants=network-online.target
Requires=docker.service

[Service]
Type=simple
User=naybinho
WorkingDirectory=/opt/naybinho/backend
ExecStart=/usr/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8081 --workers 2
Restart=on-failure
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=naybinho-backend
Environment=PYTHONUNBUFFERED=1
Environment=NAYBINHO_ENV=production

[Install]
WantedBy=multi-user.target
UNITEOF

    cat > "${squash_dir}/etc/systemd/system/naybinho-frontend.service" <<'UNITEOF'
[Unit]
Description=NayBinho NAS Frontend (Nginx)
After=network-online.target naybinho-backend.service
Wants=network-online.target

[Service]
Type=forking
ExecStartPre=/usr/sbin/nginx -t
ExecStart=/usr/sbin/nginx
ExecReload=/bin/kill -s HUP $MAINPID
ExecStop=/bin/kill -s QUIT $MAINPID
PrivateTmp=true
Restart=on-failure

[Install]
WantedBy=multi-user.target
UNITEOF

    cat > "${squash_dir}/etc/systemd/system/naybinho-storage.service" <<'UNITEOF'
[Unit]
Description=NayBinho NAS Storage Initialization
After=local-fs.target
Before=naybinho-backend.service

[Service]
Type=oneshot
RemainAfterExit=yes
ExecStart=/opt/naybinho/scripts/storage-init.sh
StandardOutput=journal
StandardError=journal
SyslogIdentifier=naybinho-storage

[Install]
WantedBy=multi-user.target
UNITEOF

    # Habilitar serviços
    chroot_exec "
        systemctl mask subiquity.service subiquity-server.service subiquity-ui.service 2>/dev/null || true
        systemctl enable naybinho-installer.service 2>/dev/null || true
        systemctl enable docker 2>/dev/null || true
        systemctl enable naybinho-backend.service 2>/dev/null || true
        systemctl enable naybinho-frontend.service 2>/dev/null || true
        systemctl enable naybinho-storage.service 2>/dev/null || true
        systemctl enable redis-server 2>/dev/null || true
        systemctl enable redis 2>/dev/null || true
        systemctl enable fail2ban 2>/dev/null || true
        systemctl enable smartd 2>/dev/null || true
        systemctl enable smartmontools 2>/dev/null || true
        systemctl enable mdadm 2>/dev/null || true
        systemctl enable ufw 2>/dev/null || true
    " || true

    # --- Configurar GRUB ---
    info "Configurando GRUB..."
    cp "${SCRIPT_DIR}/grub.cfg" "${squash_dir}/etc/default/grub.d/naybinho.cfg" 2>/dev/null || true

    # --- Substituir Plymouth (tela de boot) por tema NayBinho NAS ---
    info "Configurando Plymouth NayBinho NAS (removendo splash Ubuntu)..."
    # Criar tema Plymouth texto simples com identidade NayBinho
    mkdir -p "${squash_dir}/usr/share/plymouth/themes/naybinho"
    cat > "${squash_dir}/usr/share/plymouth/themes/naybinho/naybinho.plymouth" <<'PLYMOUTHEOF'
[Plymouth Theme]
Name=NayBinho NAS
Description=NayBinho NAS Boot Splash
ModuleName=script

[script]
ImageDir=/usr/share/plymouth/themes/naybinho
ScriptFile=/usr/share/plymouth/themes/naybinho/naybinho.script
PLYMOUTHEOF

    cat > "${squash_dir}/usr/share/plymouth/themes/naybinho/naybinho.script" <<'SCRIPTEOF'
Window.SetBackgroundTopColor(0.00, 0.03, 0.08);
Window.SetBackgroundBottomColor(0.00, 0.01, 0.04);

logo_image = Image("logo.png");
if (logo_image) {
    logo_sprite = Sprite(logo_image);
    logo_sprite.SetX(Window.GetWidth()  / 2 - logo_image.GetWidth()  / 2);
    logo_sprite.SetY(Window.GetHeight() / 2 - logo_image.GetHeight() / 2 - 40);
}

msg_image = Image.Text("NayBinho NAS  —  Iniciando...", 0.0, 0.94, 1.0, 1);
msg_sprite = Sprite(msg_image);
msg_sprite.SetX(Window.GetWidth()  / 2 - msg_image.GetWidth()  / 2);
msg_sprite.SetY(Window.GetHeight() / 2 + 60);

fun refresh_callback () {
}
Plymouth.SetRefreshFunction(refresh_callback);
SCRIPTEOF

    # Usar o logo existente (copiar como PNG se houver)
    if [[ -f "${SCRIPT_DIR}/grub-background.jpg" ]]; then
        cp "${SCRIPT_DIR}/grub-background.jpg" \
           "${squash_dir}/usr/share/plymouth/themes/naybinho/logo.png" 2>/dev/null || true
    fi

    # Registrar e ativar o tema NayBinho no chroot
    chroot_exec "
        plymouth-set-default-theme naybinho 2>/dev/null || true
        update-alternatives --set default.plymouth \
            /usr/share/plymouth/themes/naybinho/naybinho.plymouth 2>/dev/null || true
        update-initramfs -u 2>/dev/null || true
    " || true

    # Garantir que o /etc/plymouth/plymouthd.conf use nosso tema
    mkdir -p "${squash_dir}/etc/plymouth"
    cat > "${squash_dir}/etc/plymouth/plymouthd.conf" <<'PLYMOUTHCONF'
[Daemon]
Theme=naybinho
ShowDelay=0
DeviceTimeout=5
PLYMOUTHCONF

    # --- Configurar UFW (firewall) ---
    info "Configurando firewall UFW..."
    chroot_exec "
        ufw default deny incoming 2>/dev/null || true
        ufw default allow outgoing 2>/dev/null || true
        ufw allow 22/tcp comment 'SSH' 2>/dev/null || true
        ufw allow 80/tcp comment 'NayBinho Web' 2>/dev/null || true
        ufw allow 8000/tcp comment 'NayBinho API' 2>/dev/null || true
        ufw allow 8080/tcp comment 'NayBinho Dashboard' 2>/dev/null || true
        ufw allow 8081/tcp comment 'NayBinho API Alt' 2>/dev/null || true
        ufw allow 139/tcp comment 'Samba' 2>/dev/null || true
        ufw allow 445/tcp comment 'Samba' 2>/dev/null || true
        ufw allow 2049/tcp comment 'NFS' 2>/dev/null || true
        ufw allow 2049/udp comment 'NFS' 2>/dev/null || true
    " || true

    # --- Configurar MOTD ---
    info "Configurando MOTD..."
    cat > "${squash_dir}/etc/motd" <<'MOTDEOF'

  ███╗   ██╗ █████╗ ██╗   ██╗██████╗ ██╗███╗   ██╗██╗  ██╗ ██████╗
  ████╗  ██║██╔══██╗╚██╗ ██╔╝██╔══██╗██║████╗  ██║██║  ██║██╔═══██╗
  ██╔██╗ ██║███████║ ╚████╔╝ ██████╔╝██║██╔██╗ ██║███████║██║   ██║
  ██║╚██╗██║██╔══██║  ╚██╔╝  ██╔══██╗██║██║╚██╗██║██╔══██║██║   ██║
  ██║ ╚████║██║  ██║   ██║   ██████╔╝██║██║ ╚████║██║  ██║╚██████╔╝
  ╚═╝  ╚═══╝╚═╝  ╚═╝   ╚═╝   ╚═════╝ ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝ ╚═════╝

  NayBinho NAS — Home Lab OS
  Dashboard: http://<IP>:8080
  Docs:      https://naybinho.io/docs

MOTDEOF

    # --- Limpeza no chroot ---
    info "Limpando caches no chroot..."
    chroot_exec "apt-get clean && apt-get autoremove -y && rm -rf /tmp/* /var/tmp/*"
    rm -f "${squash_dir}/etc/resolv.conf"

    # Desmontar filesystems do chroot
    info "Desmontando ambiente chroot..."
    umount -l "${squash_dir}/run"  2>/dev/null || true
    umount -l "${squash_dir}/sys"  2>/dev/null || true
    umount -l "${squash_dir}/proc" 2>/dev/null || true
    umount -l "${squash_dir}/dev/pts" 2>/dev/null || true
    umount -l "${squash_dir}/dev"  2>/dev/null || true

    info "Customização do filesystem concluída."
}

# ---------------------------------------------------------------------------
# Passo 6 — Recompactar squashfs principal
# ---------------------------------------------------------------------------
repack_squashfs() {
    step "Recompactando sistema de arquivos principal (squashfs)"

    local extract_dir="${BUILD_DIR}/iso-extract"
    local squash_dir="${BUILD_DIR}/squashfs-root"
    local squash_out="${extract_dir}/casper/${TARGET_SQUASH_NAME:-ubuntu-server-minimal.squashfs}"

    info "Atualizando a camada principal do sistema em ${squash_out}..."
    rm -f "${squash_out}"
    mksquashfs "${squash_dir}" "${squash_out}" \
        -comp zstd \
        -Xcompression-level 15 \
        2>&1 | tee -a "${LOG_FILE}" || \
    mksquashfs "${squash_dir}" "${squash_out}" \
        -comp xz \
        2>&1 | tee -a "${LOG_FILE}"

    info "Atualizando manifest do filesystem..."
    chroot "${squash_dir}" dpkg-query -W --showformat='${Package} ${Version}\n' \
        > "${extract_dir}/casper/filesystem.manifest" 2>/dev/null || true

    local squash_size
    squash_size=$(du -sx --block-size=1 "${squash_dir}" 2>/dev/null | cut -f1 || echo "0")
    printf "%d" "${squash_size}" > "${extract_dir}/casper/filesystem.size" 2>/dev/null || true

    # Atualizar o initrd e kernel na ISO se foram gerados novos no chroot
    local new_initrd
    new_initrd=$(ls -t "${squash_dir}/boot"/initrd.img* 2>/dev/null | head -1 || true)
    if [[ -n "${new_initrd}" && -f "${new_initrd}" ]]; then
        info "Atualizando /casper/initrd com novo initramfs NayBinho (${new_initrd})..."
        cp "${new_initrd}" "${extract_dir}/casper/initrd"
    fi
    local new_vmlinuz
    new_vmlinuz=$(ls -t "${squash_dir}/boot"/vmlinuz* 2>/dev/null | head -1 || true)
    if [[ -n "${new_vmlinuz}" && -f "${new_vmlinuz}" ]]; then
        info "Atualizando /casper/vmlinuz com kernel NayBinho (${new_vmlinuz})..."
        cp "${new_vmlinuz}" "${extract_dir}/casper/vmlinuz"
    fi

    info "squashfs principal gerado: $(du -sh "${squash_out}" | cut -f1)"
}

# ---------------------------------------------------------------------------
# Passo 6b — Purgar Subiquity e injetar Instalador NayBinho em todas as camadas
# ---------------------------------------------------------------------------
patch_installer_squashfs() {
    step "Substituindo Subiquity (Ubuntu Installer) por NayBinho Installer em todas as camadas"

    local extract_dir="${BUILD_DIR}/iso-extract"
    local installer_dir="${BUILD_DIR}/layer-squashfs-root"
    local main_squash="${TARGET_SQUASH_NAME:-ubuntu-server-minimal.squashfs}"

    info "Inspecionando camadas squashfs em ${extract_dir}/casper/..."
    for sq in "${extract_dir}/casper/"*.squashfs; do
        [[ -f "${sq}" ]] || continue
        local sq_file="$(basename "${sq}")"

        # Pular a camada principal mínima que já foi regerada no passo anterior
        if [[ "${sq_file}" == "${main_squash}" ]]; then
            info "Camada principal ${sq_file} já tratada."
            continue
        fi

        info "Processando camada complementar: ${sq_file}..."
        rm -rf "${installer_dir}"
        mkdir -p "${installer_dir}"

        unsquashfs -f -d "${installer_dir}" "${sq}" >/dev/null 2>&1 || {
            warn "Falha ao descompactar ${sq_file}, pulando."
            continue
        }

        # 1. Purgar completamente qualquer serviço ou binário do Subiquity e Curtin
        find "${installer_dir}" -name "*subiquity*" -exec rm -rf {} + 2>/dev/null || true
        find "${installer_dir}" -name "*curtin*" -exec rm -rf {} + 2>/dev/null || true
        rm -rf "${installer_dir}/snap/subiquity" 2>/dev/null || true
        rm -f "${installer_dir}/usr/bin/subiquity" 2>/dev/null || true
        rm -f "${installer_dir}/usr/bin/curtin" 2>/dev/null || true

        # 2. Mascarar todos os serviços do Subiquity para /dev/null
        mkdir -p "${installer_dir}/etc/systemd/system/multi-user.target.wants"
        mkdir -p "${installer_dir}/etc/systemd/system/getty.target.wants"
        for svc in subiquity.service subiquity-server.service subiquity-ui.service \
                   subiquity-ui@tty1.service subiquity-ui@.service subiquity.target \
                   snap.subiquity.subiquity.service snap.subiquity.subiquity-server.service \
                   curtin.service; do
            ln -sf /dev/null "${installer_dir}/etc/systemd/system/${svc}" 2>/dev/null || true
            rm -f "${installer_dir}/etc/systemd/system/multi-user.target.wants/${svc}" 2>/dev/null || true
            rm -f "${installer_dir}/etc/systemd/system/getty.target.wants/${svc}" 2>/dev/null || true
        done

        # 3. Injetar o assistente de instalação do NayBinho NAS
        mkdir -p "${installer_dir}/opt/naybinho/system/scripts"
        mkdir -p "${installer_dir}/opt/naybinho/scripts"
        cp "${SCRIPT_DIR}/../system/scripts/wizard-install.sh" \
           "${installer_dir}/opt/naybinho/system/scripts/wizard-install.sh" 2>/dev/null || true
        cp "${SCRIPT_DIR}/../system/scripts/wizard-install.sh" \
           "${installer_dir}/opt/naybinho/scripts/wizard-install.sh" 2>/dev/null || true
        chmod +x "${installer_dir}/opt/naybinho/system/scripts/wizard-install.sh" 2>/dev/null || true
        chmod +x "${installer_dir}/opt/naybinho/scripts/wizard-install.sh" 2>/dev/null || true

        # 4. Criar o serviço naybinho-installer no tty1
        cat > "${installer_dir}/etc/systemd/system/naybinho-installer.service" <<'UNITEOF'
[Unit]
Description=NayBinho NAS Interactive TUI Installer
After=network.target getty.target
Conflicts=getty@tty1.service subiquity.service subiquity-ui.service
Before=getty@tty1.service

[Service]
Type=idle
ExecStart=/opt/naybinho/system/scripts/wizard-install.sh
StandardInput=tty-force
StandardOutput=inherit
StandardError=inherit
TTYPath=/dev/tty1
TTYReset=yes
TTYVHangup=yes
Restart=no

[Install]
WantedBy=multi-user.target
UNITEOF

        # Habilitar o serviço no multi-user.target
        ln -sf /etc/systemd/system/naybinho-installer.service \
           "${installer_dir}/etc/systemd/system/multi-user.target.wants/naybinho-installer.service" \
           2>/dev/null || true

        # 5. Recompactar a camada
        info "Recompactando camada ${sq_file}..."
        rm -f "${sq}"
        mksquashfs "${installer_dir}" "${sq}" \
            -comp zstd -Xcompression-level 15 >/dev/null 2>&1 || \
        mksquashfs "${installer_dir}" "${sq}" \
            -comp xz >/dev/null 2>&1

        rm -rf "${installer_dir}"
        info "Camada ${sq_file} atualizada: $(du -sh "${sq}" | cut -f1)"
    done
}

# ---------------------------------------------------------------------------
# Passo 7 — Configurar bootloader e metadata
# ---------------------------------------------------------------------------
configure_bootloader() {
    step "Configurando bootloader e metadados da ISO"

    local extract_dir="${BUILD_DIR}/iso-extract"

    # Copiar GRUB customizado, imagem de fundo e tema
    info "Configurando GRUB NayBinho com Logo Oficial e Tema Cyberpunk..."
    mkdir -p "${extract_dir}/boot/grub/themes/naybinho"
    cp "${SCRIPT_DIR}/grub.cfg" "${extract_dir}/boot/grub/grub.cfg"
    if [[ -d "${extract_dir}/EFI/boot" ]]; then
        cp "${SCRIPT_DIR}/grub.cfg" "${extract_dir}/EFI/boot/grub.cfg" 2>/dev/null || true
    fi
    if [[ -f "${extract_dir}/boot/grub/loopback.cfg" ]]; then
        cp "${SCRIPT_DIR}/grub.cfg" "${extract_dir}/boot/grub/loopback.cfg" 2>/dev/null || true
    fi
    if [[ -f "${SCRIPT_DIR}/grub-background.jpg" ]]; then
        cp "${SCRIPT_DIR}/grub-background.jpg" "${extract_dir}/boot/grub/background.jpg"
        cp "${SCRIPT_DIR}/grub-background.jpg" "${extract_dir}/boot/grub/themes/naybinho/background.jpg"
    fi
    if [[ -f "${SCRIPT_DIR}/theme/naybinho/theme.txt" ]]; then
        cp "${SCRIPT_DIR}/theme/naybinho/theme.txt" "${extract_dir}/boot/grub/themes/naybinho/theme.txt"
    fi

    # Atualizar metadados
    info "Atualizando metadados da ISO..."
    cat > "${extract_dir}/.disk/info" <<EOF
NayBinho NAS ${NAYBINHO_VERSION} "${ARCH}" - Release $(date +%Y%m%d)
EOF

    cat > "${extract_dir}/.disk/release_notes_url" <<EOF
https://naybinho.io/releases/${NAYBINHO_VERSION}
EOF

    # Atualizar checksums internos da ISO
    info "Recalculando checksums internos..."
    (cd "${extract_dir}" && find . -type f ! -name "md5sum.txt" ! -path "./.git/*" \
        -exec md5sum {} \; > md5sum.txt)

    info "Bootloader configurado."
}

# ---------------------------------------------------------------------------
# Passo 8 — Gerar ISO final
# ---------------------------------------------------------------------------
generate_iso() {
    step "Gerando ISO final bootável (UEFI + BIOS): ${ISO_OUTPUT_NAME}"

    local extract_dir="${BUILD_DIR}/iso-extract"
    local iso_out="${OUTPUT_DIR}/${ISO_OUTPUT_NAME}"
    local orig_iso="${CACHE_DIR}/${UBUNTU_ISO_NAME}"

    info "Capturando opções de boot nativas da ISO Ubuntu (MBR, EFI, El Torito)..."
    local mkiso_cmd="${BUILD_DIR}/run_xorriso.sh"
    echo "#!/bin/bash" > "${mkiso_cmd}"
    echo "set -e" >> "${mkiso_cmd}"
    echo -n "xorriso -as mkisofs " >> "${mkiso_cmd}"
    xorriso -indev "${orig_iso}" -report_el_torito as_mkisofs 2>/dev/null | tr '\n' ' ' >> "${mkiso_cmd}"
    echo " -V '${ISO_LABEL}' -o '${iso_out}' '${extract_dir}'" >> "${mkiso_cmd}"

    info "Gerando imagem ISO híbrida bootável (UEFI + BIOS) com xorriso..."
    bash "${mkiso_cmd}" 2>&1 | tee -a "${LOG_FILE}"

    info "Calculando checksum da ISO gerada..."
    sha256sum "${iso_out}" > "${iso_out}.sha256"

    local iso_size
    iso_size=$(du -sh "${iso_out}" | cut -f1)
    info "✅ ISO gerada com sucesso!"
    info "   Arquivo: ${iso_out}"
    info "   Tamanho: ${iso_size}"
    info "   SHA256:  $(cat "${iso_out}.sha256" | awk '{print $1}')"
}

# ---------------------------------------------------------------------------
# Passo 9 — Resumo final
# ---------------------------------------------------------------------------
print_summary() {
    local iso_out="${OUTPUT_DIR}/${ISO_OUTPUT_NAME}"
    echo ""
    echo -e "${BOLD}${GREEN}╔════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${GREEN}║         NayBinho NAS — Build Concluído!            ║${NC}"
    echo -e "${BOLD}${GREEN}╚════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  ${BOLD}ISO:${NC}     ${iso_out}"
    echo -e "  ${BOLD}SHA256:${NC}  ${iso_out}.sha256"
    echo -e "  ${BOLD}Log:${NC}     ${LOG_FILE}"
    echo ""
    echo -e "  ${BOLD}Para gravar em pendrive:${NC}"
    echo -e "  sudo dd if=${iso_out} of=/dev/sdX bs=4M status=progress"
    echo ""
    echo -e "  ${BOLD}Para testar em QEMU:${NC}"
    echo -e "  qemu-system-x86_64 -m 2048 -cdrom ${iso_out} -boot d"
    echo ""
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    parse_args "$@"
    check_root
    check_disk_space
    prepare_dirs

    log "🚀 Iniciando build NayBinho NAS v${NAYBINHO_VERSION} (${ARCH})"
    log "   Ubuntu base: ${UBUNTU_VERSION} LTS (${UBUNTU_CODENAME})"
    log "   Saída: ${OUTPUT_DIR}/${ISO_OUTPUT_NAME}"

    install_dependencies
    download_ubuntu_iso
    prepare_filesystem
    customize_filesystem
    repack_squashfs
    patch_installer_squashfs
    configure_bootloader
    generate_iso
    print_summary
}

main "$@"
