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

    # --- Configurar hostname e identidade ---
    info "Configurando identidade do sistema..."
    echo "naybinho-nas" > "${squash_dir}/etc/hostname"
    cat > "${squash_dir}/etc/hosts" <<EOF
127.0.0.1   localhost
127.0.1.1   naybinho-nas naybinho-nas.local
::1         localhost ip6-localhost ip6-loopback
ff02::1     ip6-allnodes
ff02::2     ip6-allrouters
EOF

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

    # --- Criar usuário naybinho ---
    info "Criando usuário do sistema naybinho..."
    chroot_exec "
        useradd -r -s /usr/sbin/nologin -d /opt/naybinho -c 'NayBinho NAS System' naybinho 2>/dev/null || true
        usermod -aG docker naybinho 2>/dev/null || true
    "

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
# Passo 6 — Recompactar squashfs
# ---------------------------------------------------------------------------
repack_squashfs() {
    step "Recompactando sistema de arquivos (squashfs)"

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

    info "squashfs gerado: $(du -sh "${squash_out}" | cut -f1)"
}

# ---------------------------------------------------------------------------
# Passo 7 — Configurar bootloader e metadata
# ---------------------------------------------------------------------------
configure_bootloader() {
    step "Configurando bootloader e metadados da ISO"

    local extract_dir="${BUILD_DIR}/iso-extract"

    # Copiar GRUB customizado
    info "Configurando GRUB NayBinho..."
    mkdir -p "${extract_dir}/boot/grub"
    cp "${SCRIPT_DIR}/grub.cfg" "${extract_dir}/boot/grub/grub.cfg"

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
    configure_bootloader
    generate_iso
    print_summary
}

main "$@"
