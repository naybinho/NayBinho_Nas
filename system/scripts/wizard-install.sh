#!/usr/bin/env bash
# =============================================================================
# NayBinho NAS — Assistente de Instalação Guiado (TUI Moderno v2.1)
# =============================================================================
# Totalmente customizado: sem referências ao Ubuntu ou Subiquity.
# Paleta Cyberpunk Dark Glass / Neon Cyan.
# Suporte robusto a UEFI (com fallback BOOTX64.EFI e startup.nsh) e BIOS.
# =============================================================================
set -uo pipefail

export TERM=xterm-256color
export WT_BACKTITLE="  ⚡ NayBinho NAS v1.0.0 — Home Lab OS ⚡  |  Instalador Oficial"

# ---------------------------------------------------------------------------
# Paleta Cyberpunk Dark-Glass (NEWT / Whiptail)
# ---------------------------------------------------------------------------
export NEWT_COLORS='
root=,black
window=white,black
border=cyan,black
textbox=white,black
button=black,cyan
compactbutton=white,black
title=cyan,black
listbox=white,black
actlistbox=black,cyan
actsellistbox=black,cyan
checkbox=white,black
actcheckbox=black,cyan
entry=black,cyan
label=white,black
helpbar=cyan,black
roottext=cyan,black
emptyscale=,black
fullscale=cyan,black
disabledentry=white,black
'

# ---------------------------------------------------------------------------
# 1. Verificação de root
# ---------------------------------------------------------------------------
if [[ $EUID -ne 0 ]]; then
    echo ""
    echo "  [ERRO] Este instalador precisa ser executado como root."
    echo "  Execute: sudo bash wizard-install.sh"
    echo ""
    exit 1
fi

# ---------------------------------------------------------------------------
# 2. Carregar módulos de kernel essenciais (FAT32, ext4, NLS)
# ---------------------------------------------------------------------------
modprobe vfat 2>/dev/null || true
modprobe fat 2>/dev/null || true
modprobe nls_cp437 2>/dev/null || true
modprobe nls_iso8859_1 2>/dev/null || true
modprobe ext4 2>/dev/null || true
modprobe loop 2>/dev/null || true

# ---------------------------------------------------------------------------
# 3. Garantir dependências do instalador
# ---------------------------------------------------------------------------
if ! command -v whiptail &>/dev/null; then
    apt-get update -qq 2>/dev/null || true
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq whiptail newt 2>/dev/null || true
fi
if ! command -v mkfs.vfat &>/dev/null && ! command -v mkfs.fat &>/dev/null; then
    apt-get update -qq 2>/dev/null || true
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq dosfstools 2>/dev/null || true
fi
if ! command -v rsync &>/dev/null; then
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq rsync 2>/dev/null || true
fi

# ---------------------------------------------------------------------------
# 4. Tela de Splash ASCII (NayBinho NAS)
# ---------------------------------------------------------------------------
clear
echo -e "\033[1;36m"
echo "  ╔══════════════════════════════════════════════════════════════════╗"
echo "  ║                                                                  ║"
echo "  ║    ███╗  ██╗ █████╗ ██╗   ██╗██████╗ ██╗███╗  ██╗██╗  ██╗ ██████╗ ║"
echo "  ║    ████╗ ██║██╔══██╗╚██╗ ██╔╝██╔══██╗██║████╗ ██║██║  ██║██╔═══██╗║"
echo "  ║    ██╔██╗██║███████║ ╚████╔╝ ██████╔╝██║██╔██╗██║███████║██║   ██║║"
echo "  ║    ██║╚████║██╔══██║  ╚██╔╝  ██╔══██╗██║██║╚████║██╔══██║██║   ██║║"
echo "  ║    ██║ ╚███║██║  ██║   ██║   ██████╔╝██║██║ ╚███║██║  ██║╚██████╔╝║"
echo "  ║    ╚═╝  ╚══╝╚═╝  ╚═╝   ╚═╝   ╚═════╝ ╚═╝╚═╝  ╚══╝╚═╝  ╚═╝ ╚═════╝ ║"
echo "  ║                                                                  ║"
echo "  ║            ⚡  N A S   H O M E   L A B   O S  ⚡            ║"
echo "  ║                     Instalador Oficial v1.0.0                   ║"
echo "  ║                                                                  ║"
echo "  ╚══════════════════════════════════════════════════════════════════╝"
echo -e "\033[0m"
sleep 1

# ---------------------------------------------------------------------------
# 5. Tela de Boas-Vindas
# ---------------------------------------------------------------------------
whiptail \
    --title "  Bem-vindo ao NayBinho NAS  " \
    --backtitle "${WT_BACKTITLE}" \
    --msgbox "\
Olá! Bem-vindo ao instalador oficial do NayBinho NAS!\n\
\n\
O NayBinho NAS é um sistema operacional para Home Lab e NAS pessoal,\n\
com interface web moderna, suporte a RAID, Docker e muito mais.\n\
\n\
O que este assistente faz de forma AUTOMÁTICA:\n\
  ✔  Formata apenas o disco escolhido para o sistema operacional\n\
  ✔  Preserva todos os outros HDs/SSDs (seus dados ficam seguros!)\n\
  ✔  Instala e configura bootloader UEFI (com suporte nativo a BootX64) e BIOS\n\
  ✔  Ativa o painel Web automaticamente após reiniciar\n\
\n\
Pressione ENTER para continuar ou ESC para cancelar." \
    20 74

# ---------------------------------------------------------------------------
# 6. Detectar discos disponíveis (exclui pendrive de boot e loop devices)
# ---------------------------------------------------------------------------
BOOT_DEV=""
for mpoint in /cdrom /isodevice /media/cdrom /rofs; do
    if mountpoint -q "${mpoint}" 2>/dev/null; then
        src=$(findmnt -n -o SOURCE "${mpoint}" 2>/dev/null || true)
        if [[ -n "${src}" ]]; then
            pk=$(lsblk -no PKNAME "${src}" 2>/dev/null || true)
            [[ -n "${pk}" ]] && BOOT_DEV="${pk}" && break
            BOOT_DEV=$(basename "${src}" | sed 's/[0-9]*$//;s/p[0-9]*$//')
            break
        fi
    fi
done

if [[ -z "${BOOT_DEV}" ]]; then
    BOOT_DEV=$(awk '/\/cdrom|\/isodevice/{print $1}' /proc/mounts 2>/dev/null | \
               sed 's|/dev/||;s|[0-9]*$||;s|p[0-9]*$||' | head -1 || true)
fi

DISKS_MENU=()
while IFS= read -r line; do
    name=$(echo "$line" | awk '{print $1}')
    size=$(echo "$line" | awk '{print $2}')
    tran=$(echo "$line" | awk '{print $3}')
    rota=$(echo "$line" | awk '{print $4}')
    model=$(echo "$line" | awk '{$1=$2=$3=$4=""; print $0}' | sed 's/^ *//')

    [[ "${name}" =~ ^loop ]] && continue
    [[ "${name}" =~ ^ram  ]] && continue
    [[ "${name}" =~ ^sr   ]] && continue
    [[ "${name}" =~ ^zram ]] && continue
    [[ -n "${BOOT_DEV}" && "${name}" == "${BOOT_DEV}" ]] && continue

    if [[ "${rota}" == "0" ]]; then
        tipo="SSD/NVMe"
    else
        tipo="HD"
    fi
    desc="${size}  ${tipo}  ${tran:-SATA}"
    if [[ -n "${model// }" ]]; then
        desc="${size}  —  ${model}  (${tipo})"
    fi

    DISKS_MENU+=("${name}" "${desc}")
done < <(lsblk -d -n -o NAME,SIZE,TRAN,ROTA,MODEL 2>/dev/null)

if [[ ${#DISKS_MENU[@]} -eq 0 ]]; then
    whiptail \
        --title "  Nenhum Disco Encontrado  " \
        --backtitle "${WT_BACKTITLE}" \
        --msgbox "\
Nenhum disco rígido ou SSD foi detectado para instalação.\n\
\n\
Possíveis causas:\n\
  • O disco não está conectado corretamente (cabo SATA ou NVMe)\n\
  • O controlador de disco precisa de driver adicional\n\
  • O disco já está em uso pelo pendrive de instalação\n\
\n\
Verifique as conexões e reinicie o instalador." \
        16 65
    exit 1
fi

# ---------------------------------------------------------------------------
# 7. Menu de seleção de disco
# ---------------------------------------------------------------------------
SELECTED_DISK=$(whiptail \
    --title "  Seleção do Disco de Sistema  " \
    --backtitle "${WT_BACKTITLE}" \
    --menu "\
Escolha o disco onde instalar o NayBinho NAS:\n\
\n\
  DICA: Use o menor SSD para o sistema. Os HDs maiores\n\
        ficam LIVRES para armazenar seus arquivos e RAID." \
    20 76 8 \
    "${DISKS_MENU[@]}" \
    3>&1 1>&2 2>&3) || {
    whiptail --title "Cancelado" \
        --backtitle "${WT_BACKTITLE}" \
        --msgbox "Instalação cancelada. Nenhuma alteração foi feita." 8 50
    exit 0
}

TARGET_DEV="/dev/${SELECTED_DISK}"

# ---------------------------------------------------------------------------
# 8. Confirmação com alerta claro de formatação
# ---------------------------------------------------------------------------
DISK_INFO=$(lsblk -d -n -o SIZE,MODEL "${TARGET_DEV}" 2>/dev/null | head -1 | xargs || echo "")
if ! whiptail \
    --title "  ⚠  Confirmar Formatação  " \
    --backtitle "${WT_BACKTITLE}" \
    --yesno "\
ATENÇÃO: O disco abaixo será FORMATADO!\n\
\n\
  Disco selecionado: ${TARGET_DEV}\n\
  Informações:       ${DISK_INFO}\n\
\n\
  ✔  Todos os dados NESTE DISCO serão apagados.\n\
  ✔  Outros discos conectados NÃO serão tocados.\n\
\n\
Tem certeza que deseja continuar a instalação em ${TARGET_DEV}?" \
    16 70; then
    whiptail --title "Cancelado" \
        --backtitle "${WT_BACKTITLE}" \
        --msgbox "Instalação cancelada. Nenhuma alteração foi feita nos seus discos." 8 60
    exit 0
fi

# ---------------------------------------------------------------------------
# 9. Executar instalação com barra de progresso
# ---------------------------------------------------------------------------
perform_install() {
    exec 2>/tmp/naybinho_install.err

    # Passo 1: Desmontar e limpar assinaturas antigas
    echo 5
    echo "XXX"
    echo "5"
    echo "[ 1/9 ] Preparando e limpando o disco ${TARGET_DEV}..."
    echo "XXX"
    swapoff "${TARGET_DEV}"* 2>/dev/null || true
    for p in $(ls "${TARGET_DEV}"* 2>/dev/null); do
        umount -f "${p}" 2>/dev/null || true
    done
    wipefs -af "${TARGET_DEV}" >/dev/null 2>&1 || true
    dd if=/dev/zero of="${TARGET_DEV}" bs=1M count=16 conv=notrunc >/dev/null 2>&1 || true
    sync
    sleep 1

    # Passo 2: Criar tabela de partições GPT
    echo 15
    echo "XXX"
    echo "15"
    echo "[ 2/9 ] Criando tabela de partições GPT e partições EFI / Sistema..."
    echo "XXX"
    parted -s "${TARGET_DEV}" -- mklabel gpt 2>/dev/null || true
    # Partição 1: EFI System Partition (512 MiB)
    parted -s "${TARGET_DEV}" -- mkpart "EFI" fat32 1MiB 513MiB 2>/dev/null || true
    parted -s "${TARGET_DEV}" -- set 1 esp on 2>/dev/null || true
    parted -s "${TARGET_DEV}" -- set 1 boot on 2>/dev/null || true
    # Partição 2: Root Filesystem (Restante do disco)
    parted -s "${TARGET_DEV}" -- mkpart "NAYBINHO_ROOT" ext4 513MiB 100% 2>/dev/null || true
    sync
    udevadm settle 2>/dev/null || sleep 2
    partprobe "${TARGET_DEV}" 2>/dev/null || true
    udevadm settle 2>/dev/null || sleep 2
    sleep 2

    # Passo 3: Identificar nós de partições
    echo 25
    echo "XXX"
    echo "25"
    echo "[ 3/9 ] Detectando partições criadas no kernel..."
    echo "XXX"
    if [[ "${TARGET_DEV}" =~ nvme|mmcblk ]]; then
        PART_BOOT="${TARGET_DEV}p1"
        PART_ROOT="${TARGET_DEV}p2"
    else
        PART_BOOT="${TARGET_DEV}1"
        PART_ROOT="${TARGET_DEV}2"
    fi

    for i in $(seq 1 10); do
        [[ -b "${PART_BOOT}" && -b "${PART_ROOT}" ]] && break
        sleep 1
    done

    # Passo 4: Formatar partições
    echo 35
    echo "XXX"
    echo "35"
    echo "[ 4/9 ] Formatando partições (FAT32 EFI + EXT4 Sistema)..."
    echo "XXX"
    wipefs -af "${PART_BOOT}" >/dev/null 2>&1 || true
    wipefs -af "${PART_ROOT}" >/dev/null 2>&1 || true

    # Formatar FAT32 com retentativas
    if command -v mkfs.vfat &>/dev/null; then
        mkfs.vfat -F 32 -n "NAYBINHO_EFI" "${PART_BOOT}" >/dev/null 2>&1 || \
        mkfs.vfat -F 32 "${PART_BOOT}" >/dev/null 2>&1
    elif command -v mkfs.fat &>/dev/null; then
        mkfs.fat -F 32 -n "NAYBINHO_EFI" "${PART_BOOT}" >/dev/null 2>&1 || \
        mkfs.fat -F 32 "${PART_BOOT}" >/dev/null 2>&1
    fi

    # Formatar EXT4
    mkfs.ext4 -F -L "NAYBINHO_OS" "${PART_ROOT}" >/dev/null 2>&1
    sync
    sleep 1

    # Passo 5: Montar partições de destino
    echo 45
    echo "XXX"
    echo "45"
    echo "[ 5/9 ] Montando partições de destino..."
    echo "XXX"
    TARGET_MOUNT="/mnt/naybinho_target"
    umount -l "${TARGET_MOUNT}/boot/efi" 2>/dev/null || true
    umount -l "${TARGET_MOUNT}" 2>/dev/null || true
    rm -rf "${TARGET_MOUNT}"
    mkdir -p "${TARGET_MOUNT}"

    mount -t ext4 "${PART_ROOT}" "${TARGET_MOUNT}" || {
        echo "ERRO: Não foi possível montar partição raiz ${PART_ROOT}"
        exit 1
    }

    mkdir -p "${TARGET_MOUNT}/boot/efi"
    mount -t vfat "${PART_BOOT}" "${TARGET_MOUNT}/boot/efi" 2>/dev/null || \
    mount "${PART_BOOT}" "${TARGET_MOUNT}/boot/efi" 2>/dev/null || true
    sleep 1

    # Passo 6: Copiar sistema operacional ao vivo para o disco
    echo 55
    echo "XXX"
    echo "55"
    echo "[ 6/9 ] Copiando sistema NayBinho NAS para o disco..."
    echo "        (Pode demorar alguns minutos)"
    echo "XXX"
    rsync -aAX \
        --exclude={"/dev/*","/proc/*","/sys/*","/tmp/*","/run/*","/mnt/*","/media/*","/lost+found","/cdrom/*","/isodevice/*"} \
        / "${TARGET_MOUNT}/" 2>/dev/null || true

    # Garantir que kernel Linux e initramfs estejam presentes em /boot no sistema instalado
    mkdir -p "${TARGET_MOUNT}/boot"
    if ! ls "${TARGET_MOUNT}/boot"/vmlinuz* 1>/dev/null 2>&1; then
        for k in /boot/vmlinuz* /cdrom/casper/vmlinuz; do
            if [[ -f "${k}" ]]; then
                cp "${k}" "${TARGET_MOUNT}/boot/vmlinuz-$(uname -r 2>/dev/null || echo generic)" 2>/dev/null || true
                break
            fi
        done
    fi
    if ! ls "${TARGET_MOUNT}/boot"/initrd* 1>/dev/null 2>&1; then
        for i in /boot/initrd* /cdrom/casper/initrd; do
            if [[ -f "${i}" ]]; then
                cp "${i}" "${TARGET_MOUNT}/boot/initrd.img-$(uname -r 2>/dev/null || echo generic)" 2>/dev/null || true
                break
            fi
        done
    fi

    # Passo 7: Configurar fstab e identidade
    echo 75
    echo "XXX"
    echo "75"
    echo "[ 7/9 ] Configurando sistema de arquivos (fstab)..."
    echo "XXX"
    UUID_ROOT=$(blkid -s UUID -o value "${PART_ROOT}" 2>/dev/null || echo "")
    UUID_BOOT=$(blkid -s UUID -o value "${PART_BOOT}" 2>/dev/null || echo "")
    mkdir -p "${TARGET_MOUNT}/etc"
    cat > "${TARGET_MOUNT}/etc/fstab" <<FSTABEOF
# /etc/fstab — NayBinho NAS
# <file system>                           <mount>     <type>  <options>           <dump> <pass>
UUID=${UUID_ROOT}  /           ext4    errors=remount-ro   0      1
UUID=${UUID_BOOT}  /boot/efi   vfat    umask=0077          0      2
FSTABEOF

    echo "naybinho-nas" > "${TARGET_MOUNT}/etc/hostname"
    sleep 1

    # Passo 8: Instalar bootloader GRUB (UEFI + BIOS com fallback BOOTX64.EFI)
    echo 85
    echo "XXX"
    echo "85"
    echo "[ 8/9 ] Instalando e configurando bootloader UEFI / BIOS..."
    echo "XXX"

    # Garantir que a partição EFI está montada
    if ! mountpoint -q "${TARGET_MOUNT}/boot/efi"; then
        mkdir -p "${TARGET_MOUNT}/boot/efi"
        mount -t vfat "${PART_BOOT}" "${TARGET_MOUNT}/boot/efi" 2>/dev/null || true
    fi

    # Montar bind mounts para o chroot
    for dir in dev dev/pts proc sys run; do
        mkdir -p "${TARGET_MOUNT}/${dir}"
        mount --bind "/${dir}" "${TARGET_MOUNT}/${dir}" 2>/dev/null || true
    done

    # Limpar qualquer configuração residual do grub.d e aplicar padrão válido
    rm -rf "${TARGET_MOUNT}/etc/default/grub.d"/* 2>/dev/null || true
    mkdir -p "${TARGET_MOUNT}/etc/default/grub.d"
    cat > "${TARGET_MOUNT}/etc/default/grub.d/naybinho.cfg" <<'GRUBDEFAULTEOF'
GRUB_DEFAULT=0
GRUB_TIMEOUT=3
GRUB_TIMEOUT_STYLE=menu
GRUB_DISTRIBUTOR="NayBinho NAS"
GRUB_CMDLINE_LINUX_DEFAULT="quiet console=tty1"
GRUB_CMDLINE_LINUX=""
GRUB_TERMINAL_OUTPUT="gfxterm"
GRUB_GFXMODE="1920x1080,1280x720,auto"
GRUB_GFXPAYLOAD_LINUX="keep"
GRUBDEFAULTEOF

    # Garantir symlinks para vmlinuz e initrd.img na raiz de /boot
    local latest_kernel=$(ls -v "${TARGET_MOUNT}/boot"/vmlinuz-* 2>/dev/null | tail -n 1)
    local latest_initrd=$(ls -v "${TARGET_MOUNT}/boot"/initrd.img-* 2>/dev/null | tail -n 1)
    if [[ -n "${latest_kernel}" && -f "${latest_kernel}" ]]; then
        ln -sf "$(basename "${latest_kernel}")" "${TARGET_MOUNT}/boot/vmlinuz" 2>/dev/null || true
    fi
    if [[ -n "${latest_initrd}" && -f "${latest_initrd}" ]]; then
        ln -sf "$(basename "${latest_initrd}")" "${TARGET_MOUNT}/boot/initrd.img" 2>/dev/null || true
    fi

    # Copiar tema e plano de fundo GRUB oficial
    if [[ -d /boot/grub/themes/naybinho ]]; then
        mkdir -p "${TARGET_MOUNT}/boot/grub/themes"
        cp -r /boot/grub/themes/naybinho "${TARGET_MOUNT}/boot/grub/themes/" 2>/dev/null || true
    fi
    if [[ -f /boot/grub/background.jpg ]]; then
        cp /boot/grub/background.jpg "${TARGET_MOUNT}/boot/grub/background.jpg" 2>/dev/null || true
    fi

    # 1. Instalar GRUB UEFI padrão (com id NayBinhoNAS)
    chroot "${TARGET_MOUNT}" grub-install \
        --target=x86_64-efi \
        --efi-directory=/boot/efi \
        --bootloader-id=NayBinhoNAS \
        --recheck 2>/dev/null || true

    # 2. Instalar GRUB UEFI modo REMOVÍVEL (cria automaticamente /EFI/BOOT/BOOTX64.EFI)
    chroot "${TARGET_MOUNT}" grub-install \
        --target=x86_64-efi \
        --efi-directory=/boot/efi \
        --bootloader-id=NayBinhoNAS \
        --removable \
        --recheck 2>/dev/null || true

    # 3. Garantir cópia de segurança de BOOTX64.EFI em EFI/BOOT/ (Universal UEFI Fallback)
    mkdir -p "${TARGET_MOUNT}/boot/efi/EFI/BOOT"
    mkdir -p "${TARGET_MOUNT}/boot/efi/EFI/boot"
    for efi_src in \
        "${TARGET_MOUNT}/boot/efi/EFI/NayBinhoNAS/grubx64.efi" \
        "${TARGET_MOUNT}/boot/efi/EFI/ubuntu/grubx64.efi" \
        "${TARGET_MOUNT}/usr/lib/grub/x86_64-efi/monolithic/grubx64.efi"; do
        if [[ -f "${efi_src}" ]]; then
            cp "${efi_src}" "${TARGET_MOUNT}/boot/efi/EFI/BOOT/BOOTX64.EFI" 2>/dev/null || true
            cp "${efi_src}" "${TARGET_MOUNT}/boot/efi/EFI/BOOT/bootx64.efi" 2>/dev/null || true
            cp "${efi_src}" "${TARGET_MOUNT}/boot/efi/EFI/boot/bootx64.efi" 2>/dev/null || true
            break
        fi
    done

    # 4. Criar script startup.nsh na raiz da partição EFI (para auto-iniciar se cair na Shell UEFI)
    cat > "${TARGET_MOUNT}/boot/efi/startup.nsh" <<'NSHEOF'
@echo -off
\EFI\BOOT\BOOTX64.EFI
\EFI\NayBinhoNAS\grubx64.efi
NSHEOF

    # 5. Instalar também GRUB para MBR/BIOS legado (caso a placa-mãe use CSM/Legacy)
    chroot "${TARGET_MOUNT}" grub-install \
        --target=i386-pc \
        "${TARGET_DEV}" \
        --recheck 2>/dev/null || true

    # 6. Atualizar lista de inicialização pelo grub-mkconfig
    chroot "${TARGET_MOUNT}" update-grub 2>/dev/null || true

    # 7. Criar diretamente o grub.cfg independente oficial do NayBinho NAS como garantia
    local kernel_name=$(basename "$(ls -v "${TARGET_MOUNT}/boot"/vmlinuz-* 2>/dev/null | tail -n 1)")
    local initrd_name=$(basename "$(ls -v "${TARGET_MOUNT}/boot"/initrd.img-* 2>/dev/null | tail -n 1)")
    mkdir -p "${TARGET_MOUNT}/boot/grub"
    cat > "${TARGET_MOUNT}/boot/grub/grub.cfg" <<GRUBCFGEOF
set default="0"
set timeout=3

search --no-floppy --fs-uuid --set=root ${UUID_ROOT}

menuentry "NayBinho NAS" {
    linux /boot/${kernel_name} root=UUID=${UUID_ROOT} ro quiet console=tty1
    initrd /boot/${initrd_name}
}
menuentry "NayBinho NAS (Fallback Symlink)" {
    linux /boot/vmlinuz root=UUID=${UUID_ROOT} ro quiet console=tty1
    initrd /boot/initrd.img
}
GRUBCFGEOF

    # 8. Gravar arquivos de redirecionamento EFI para apontar sempre para a partição root
    for efi_cfg_dir in \
        "${TARGET_MOUNT}/boot/efi" \
        "${TARGET_MOUNT}/boot/efi/EFI/BOOT" \
        "${TARGET_MOUNT}/boot/efi/EFI/boot" \
        "${TARGET_MOUNT}/boot/efi/EFI/NayBinhoNAS" \
        "${TARGET_MOUNT}/boot/efi/EFI/ubuntu"; do
        mkdir -p "${efi_cfg_dir}"
        cat > "${efi_cfg_dir}/grub.cfg" <<EFIFORWARD
search.fs_uuid ${UUID_ROOT} root
if [ -z "\$root" ]; then
    search.file /boot/grub/grub.cfg root
fi
set prefix=(\$root)'/boot/grub'
configfile \$prefix/grub.cfg
EFIFORWARD
    done

    # Desabilitar o instalador no sistema instalado e habilitar serviços NayBinho
    chroot "${TARGET_MOUNT}" systemctl disable naybinho-installer.service 2>/dev/null || true
    chroot "${TARGET_MOUNT}" systemctl enable  docker.service              2>/dev/null || true
    chroot "${TARGET_MOUNT}" systemctl enable  naybinho-backend.service    2>/dev/null || true
    chroot "${TARGET_MOUNT}" systemctl enable  naybinho-frontend.service   2>/dev/null || true

    # Desmontar bind mounts
    for dir in run sys proc dev/pts dev; do
        umount -l "${TARGET_MOUNT}/${dir}" 2>/dev/null || true
    done
    sleep 1
    # Passo 9: Finalizar e desmontar
    echo 95
    echo "XXX"
    echo "95"
    echo "[ 9/9 ] Finalizando e sincronizando discos..."
    echo "XXX"
    sync
    umount -l "${TARGET_MOUNT}/boot/efi" 2>/dev/null || true
    umount -l "${TARGET_MOUNT}"          2>/dev/null || true
    sleep 1

    echo 100
    echo "XXX"
    echo "100"
    echo "Instalação concluída com sucesso!"
    echo "XXX"
    sleep 1
}

perform_install | whiptail \
    --title "  Instalando NayBinho NAS...  " \
    --backtitle "${WT_BACKTITLE}" \
    --gauge "\nInstalando o sistema operacional. Por favor, aguarde...\n" \
    10 72 0

# ---------------------------------------------------------------------------
# 10. Obter IP local da máquina
# ---------------------------------------------------------------------------
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "192.168.X.X")
[[ -z "${LOCAL_IP}" ]] && LOCAL_IP="192.168.X.X"

# ---------------------------------------------------------------------------
# 11. Tela de sucesso com instruções de acesso
# ---------------------------------------------------------------------------
whiptail \
    --title "  ✔  Instalação Concluída com Sucesso!  " \
    --backtitle "${WT_BACKTITLE}" \
    --msgbox "\
O NayBinho NAS foi instalado com sucesso!\n\
\n\
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\
  Disco instalado:   ${TARGET_DEV}\n\
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\
\n\
PRÓXIMOS PASSOS:\n\
\n\
  1.  Remova o pendrive de instalação do servidor.\n\
  2.  Reinicie o servidor.\n\
  3.  Abra o navegador em qualquer PC ou celular\n\
      conectado na mesma rede e acesse:\n\
\n\
      http://${LOCAL_IP}:8080\n\
      http://naybinho-nas.local:8080\n\
\n\
  Login inicial:\n\
      Usuário:  admin\n\
      Senha:    naybinho\n\
\n\
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" \
    26 68

# ---------------------------------------------------------------------------
# 12. Oferecer reinicialização
# ---------------------------------------------------------------------------
if whiptail \
    --title "  Reiniciar Servidor  " \
    --backtitle "${WT_BACKTITLE}" \
    --yesno "\
Deseja reiniciar o servidor agora?\n\
\n\
  SIM  → O servidor reinicia e o NayBinho NAS inicia automaticamente.\n\
  NAO  → Você pode reiniciar manualmente quando quiser (reboot)." \
    12 68; then
    clear
    echo ""
    echo -e "\033[1;36m  Reiniciando o servidor... Obrigado por escolher o NayBinho NAS!\033[0m"
    echo ""
    sleep 2
    reboot
else
    clear
    echo ""
    echo -e "\033[1;36m  Instalação concluída!\033[0m"
    echo -e "  Digite \033[1mreboot\033[0m para reiniciar quando estiver pronto."
    echo ""
fi
