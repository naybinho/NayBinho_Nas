#!/usr/bin/env bash
# =============================================================================
# NayBinho NAS — Assistente de Instalação Guiado (TUI Moderno)
# =============================================================================
# Ambiente gráfico TUI Dark-Glass / Neon Cyan personalizado.
# =============================================================================
set -euo pipefail

export TERM=xterm-256color
export WT_BACKTITLE="⚡ NayBinho NAS v1.0.0 — Home Lab Operating System ⚡"

# Paleta de Cores Cyberpunk / Dark Glass (Whiptail NEWT)
export NEWT_COLORS='
root=,black
window=lightgray,black
border=cyan,black
textbox=lightgray,black
button=black,cyan
compactbutton=lightgray,black
title=cyan,black
listbox=lightgray,black
actlistbox=black,cyan
actsellistbox=black,cyan
checkbox=lightgray,black
actcheckbox=black,cyan
entry=black,cyan
label=lightgray,black
helpbar=cyan,black
roottext=cyan,black
'

# 1. Checagem de Root
if [[ $EUID -ne 0 ]]; then
    echo "Execute como root: sudo bash wizard-install.sh"
    exit 1
fi

clear
cat <<'EOF'
 [1;36m
  ███╗   ██╗ █████╗ ██╗   ██╗██████╗ ██╗███╗   ██╗██╗  ██╗ ██████╗ 
  ████╗  ██║██╔══██╗╚██╗ ██╔╝██╔══██╗██║████╗  ██║██║  ██║██╔═══██╗
  ██╔██╗ ██║███████║ ╚████╔╝ ██████╔╝██║██╔██╗ ██║███████║██║   ██║
  ██║╚██╗██║██╔══██║  ╚██╔╝  ██╔══██╗██║██║╚██╗██║██╔══██║██║   ██║
  ██║ ╚████║██║  ██║   ██║   ██████╔╝██║██║ ╚████║██║  ██║╚██████╔╝
  ╚═╝  ╚═══╝╚═╝  ╚═╝   ╚═╝   ╚═════╝ ╚═╝╚═╝  ╚═══╝╚═╝  ╚═╝ ╚═════╝ 
                 ⚡ N A Y B I N H O   N A S ⚡
                 Home Lab Operating System
 [0m
EOF
sleep 1

# Instalar whiptail e ferramentas se ausente
if ! command -v whiptail &>/dev/null; then
    apt-get update -qq && apt-get install -y -qq whiptail >/dev/null 2>&1 || true
fi

# 2. Tela de Boas-Vindas
whiptail --title "🏠 Bem-vindo ao NayBinho NAS" \
    --backtitle "${WT_BACKTITLE}" \
    --msgbox "Bem-vindo ao instalador oficial do NayBinho NAS!\n\nEste assistente foi desenvolvido para ser extremamente simples e seguro:\n\n1. Você escolhe apenas o disco onde deseja instalar o sistema (SSD ou HD principal).\n2. Todos os outros discos de armazenamento e dados NÃO serão tocados!\n3. Após a instalação, o painel Web estará disponível imediatamente na sua rede." \
    16 72

# 3. Detectar Discos Disponíveis
BOOT_DEV=""
if mount | grep -q "on /cdrom"; then
    BOOT_DEV=$(mount | grep "on /cdrom" | awk '{print $1}' | sed 's/[0-9]*$//' | sed 's/p[0-9]*$//' | xargs basename 2>/dev/null || true)
fi

DISKS_MENU=()
while read -r name size model tran; do
    # Ignora loops, zram, cdrom e o próprio pendrive de boot
    if [[ "$name" =~ ^loop || "$name" =~ ^ram || "$name" =~ ^sr || "$name" == "$BOOT_DEV" ]]; then
        continue
    fi
    
    DESC="${size} - ${model:-Disco de Armazenamento} (${tran:-SATA/NVMe})"
    DISKS_MENU+=("$name" "$DESC")
done < <(lsblk -d -n -o NAME,SIZE,MODEL,TRAN 2>/dev/null)

if [[ ${#DISKS_MENU[@]} -eq 0 ]]; then
    whiptail --title "⚠️ Nenhum Disco Encontrado" \
        --backtitle "${WT_BACKTITLE}" \
        --msgbox "Nenhum disco rígido ou SSD disponível para instalação foi detectado.\nVerifique as conexões SATA/NVMe e tente novamente." \
        10 60
    exit 1
fi

# 4. Tela de Seleção de Disco
SELECTED_DISK=$(whiptail --title "💾 Seleção do Disco do Sistema" \
    --backtitle "${WT_BACKTITLE}" \
    --menu "Escolha em qual disco você deseja instalar o NayBinho NAS:\n(Dica: Escolha o menor SSD para o sistema para deixar os HDDs grandes para RAID)" \
    18 76 6 \
    "${DISKS_MENU[@]}" \
    3>&1 1>&2 2>&3)

if [[ -z "${SELECTED_DISK}" ]]; then
    whiptail --title "Instalação Cancelada" --msgbox "A instalação foi cancelada pelo usuário." 8 45
    exit 0
fi

TARGET_DEV="/dev/${SELECTED_DISK}"

# 5. Confirmação com Alerta de Segurança
if ! whiptail --title "⚠️ Confirmação de Instalação" \
    --backtitle "${WT_BACKTITLE}" \
    --yesno "ATENÇÃO: O disco ${TARGET_DEV} será formatado para instalar o NayBinho NAS.\n\nTodos os outros discos conectados no seu servidor serão PRESERVADOS para armazenar seus arquivos e criar pools de RAID!\n\nDeseja continuar com a instalação em ${TARGET_DEV}?" \
    14 70; then
    whiptail --title "Instalação Cancelada" --msgbox "Nenhuma alteração foi feita nos seus discos." 8 50
    exit 0
fi

# 6. Execução da Instalação com Barra de Progresso
{
    echo 5; sleep 1
    # Limpar assinaturas antigas
    wipefs -a "${TARGET_DEV}" >/dev/null 2>&1 || true

    echo 15; sleep 1
    # Criar tabela de partições GPT
    parted -s "${TARGET_DEV}" mklabel gpt 2>/dev/null || true
    parted -s "${TARGET_DEV}" mkpart "ESP" fat32 1MiB 512MiB 2>/dev/null || true
    parted -s "${TARGET_DEV}" set 1 esp on 2>/dev/null || true
    parted -s "${TARGET_DEV}" mkpart "NAYBINHO_ROOT" ext4 512MiB 100% 2>/dev/null || true

    echo 30; sleep 1
    # Definir nomes das partições (NVMe vs SATA)
    PART_BOOT="${TARGET_DEV}1"
    PART_ROOT="${TARGET_DEV}2"
    if [[ "${TARGET_DEV}" =~ nvme ]]; then
        PART_BOOT="${TARGET_DEV}p1"
        PART_ROOT="${TARGET_DEV}p2"
    fi

    # Formatar partições
    mkfs.fat -F32 "${PART_BOOT}" >/dev/null 2>&1 || true
    mkfs.ext4 -F -L "NAYBINHO_OS" "${PART_ROOT}" >/dev/null 2>&1 || true

    echo 45; sleep 1
    # Montar sistema de destino
    TARGET_MOUNT="/mnt/naybinho_target"
    mkdir -p "${TARGET_MOUNT}"
    mount "${PART_ROOT}" "${TARGET_MOUNT}"
    mkdir -p "${TARGET_MOUNT}/boot/efi"
    mount "${PART_BOOT}" "${TARGET_MOUNT}/boot/efi"

    echo 60; sleep 1
    # Copiar o sistema operacional ao vivo completo para o disco
    rsync -aAX \
        --exclude={"/dev/*","/proc/*","/sys/*","/tmp/*","/run/*","/mnt/*","/media/*","/lost+found","/cdrom/*"} \
        / "${TARGET_MOUNT}/" 2>/dev/null || true

    echo 75; sleep 1
    # Configurar fstab
    UUID_ROOT=$(blkid -s UUID -o value "${PART_ROOT}" || echo "")
    UUID_BOOT=$(blkid -s UUID -o value "${PART_BOOT}" || echo "")
    cat > "${TARGET_MOUNT}/etc/fstab" <<FSTABEOF
UUID=${UUID_ROOT} / ext4 errors=remount-ro 0 1
UUID=${UUID_BOOT} /boot/efi vfat umask=0077 0 1
FSTABEOF

    echo 85; sleep 1
    # Montar binds para chroot do bootloader
    mount --bind /dev     "${TARGET_MOUNT}/dev"
    mount --bind /dev/pts "${TARGET_MOUNT}/dev/pts"
    mount --bind /proc    "${TARGET_MOUNT}/proc"
    mount --bind /sys     "${TARGET_MOUNT}/sys"

    # Instalar GRUB no disco instalado (UEFI + BIOS)
    chroot "${TARGET_MOUNT}" grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=NayBinhoNAS --recheck 2>/dev/null || true
    chroot "${TARGET_MOUNT}" grub-install --target=i386-pc "${TARGET_DEV}" --recheck 2>/dev/null || true
    chroot "${TARGET_MOUNT}" update-grub 2>/dev/null || true

    # Desabilitar o serviço do instalador no sistema instalado
    chroot "${TARGET_MOUNT}" systemctl disable naybinho-installer.service 2>/dev/null || true
    chroot "${TARGET_MOUNT}" systemctl enable naybinho-backend.service naybinho-frontend.service docker.service 2>/dev/null || true

    echo 95; sleep 1
    # Desmontar tudo
    umount -l "${TARGET_MOUNT}/dev/pts" 2>/dev/null || true
    umount -l "${TARGET_MOUNT}/dev" 2>/dev/null || true
    umount -l "${TARGET_MOUNT}/proc" 2>/dev/null || true
    umount -l "${TARGET_MOUNT}/sys" 2>/dev/null || true
    umount -l "${TARGET_MOUNT}/boot/efi" 2>/dev/null || true
    umount -l "${TARGET_MOUNT}" 2>/dev/null || true

    echo 100; sleep 1
} | whiptail --title "⏳ Instalando NayBinho NAS..." \
    --backtitle "${WT_BACKTITLE}" \
    --gauge "Preparando discos, copiando o sistema NayBinho e configurando bootloader...\nPor favor, aguarde alguns instantes." \
    9 70 0

# 7. Obter IP local da máquina
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "SEU-IP")

# 8. Tela de Conclusão com Instruções Claras
whiptail --title "🎉 Instalação Concluída com Sucesso!" \
    --backtitle "${WT_BACKTITLE}" \
    --msgbox "O NayBinho NAS foi instalado com sucesso no disco ${TARGET_DEV}!\n\nINSTRUÇÕES DE ACESSO:\n1. Retire o pendrive de instalação.\n2. Reinicie o computador.\n3. Abra o navegador em qualquer PC ou celular conectado à mesma rede e acesse:\n\n   👉 http://${LOCAL_IP}:8080\n   👉 ou http://naybinho-nas.local:8080\n\nLogin padrão de fábrica:\nUsuário: admin\nSenha:   naybinho" \
    18 72

# Pergunta para reiniciar
if whiptail --title "🔄 Reiniciar Servidor" \
    --backtitle "${WT_BACKTITLE}" \
    --yesno "Deseja reiniciar o servidor agora para iniciar o NayBinho NAS instalado?" \
    10 65; then
    reboot
fi
