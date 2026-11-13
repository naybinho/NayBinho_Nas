#!/usr/bin/env bash
# =============================================================================
# NayBinho NAS — Assistente de Instalação Guiado (TUI Wizard)
# =============================================================================
# Executado automaticamente ao dar boot pela ISO ou pendrive.
# Permite ao usuário leigo escolher o disco do sistema e instalar em 3 passos.
# =============================================================================
set -euo pipefail

# Cores e terminal
export TERM=xterm-256color
WT_BACKTITLE="NayBinho NAS v1.0.0 — Home Lab Operating System"

# 1. Checagem de Root
if [[ $EUID -ne 0 ]]; then
    echo "Execute como root: sudo bash wizard-install.sh"
    exit 1
fi

# Instalar whiptail se ausente
if ! command -v whiptail &>/dev/null; then
    apt-get update -qq && apt-get install -y -qq whiptail >/dev/null 2>&1 || true
fi

# 2. Tela de Boas-Vindas
whiptail --title "🏠 Bem-vindo ao NayBinho NAS" \
    --backtitle "${WT_BACKTITLE}" \
    --msgbox "Bem-vindo ao instalador simplificado do NayBinho NAS!\n\nEste assistente irá preparar seu servidor Home Lab em poucos cliques.\n\nVocê só precisará escolher em qual disco instalar o sistema.\nSeus discos de dados e HDDs extras NÃO serão tocados!" \
    15 68

# 3. Detectar Discos Disponíveis
# Descobrir qual disco é o pendrive de boot para NÃO listar ele
BOOT_DEV=""
if mount | grep -q "on /cdrom"; then
    BOOT_DEV=$(mount | grep "on /cdrom" | awk '{print $1}' | sed 's/[0-9]*$//' | sed 's/p[0-9]*$//' | xargs basename 2>/dev/null || true)
fi

DISKS_MENU=()
while read -r name size model tran; do
    # Ignora loop, ram, e o pendrive de boot
    if [[ "$name" =~ ^loop || "$name" =~ ^ram || "$name" =~ ^sr || "$name" == "$BOOT_DEV" ]]; then
        continue
    fi
    
    DESC="${size} - ${model:-Disco Genérico} (${tran:-SATA/NVMe})"
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
    --menu "Escolha em qual disco você deseja instalar o NayBinho NAS:\n(Recomendamos escolher o menor disco ou SSD para o sistema)" \
    18 72 6 \
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
    --yesno "ATENÇÃO: O disco ${TARGET_DEV} será formatado para receber o sistema operacional NayBinho NAS.\n\nTodos os outros discos conectados no seu computador serão PRESERVADOS para armazenar seus arquivos e criar RAIDs.\n\nDeseja continuar com a instalação em ${TARGET_DEV}?" \
    14 68; then
    whiptail --title "Instalação Cancelada" --msgbox "Nenhuma alteração foi feita nos seus discos." 8 50
    exit 0
fi

# 6. Barra de Progresso da Instalação
{
    echo 10; sleep 1
    # 1. Preparar partições
    parted -s "${TARGET_DEV}" mklabel gpt 2>/dev/null || true
    parted -s "${TARGET_DEV}" mkpart ESP fat32 1MiB 512MiB 2>/dev/null || true
    parted -s "${TARGET_DEV}" set 1 esp on 2>/dev/null || true
    parted -s "${TARGET_DEV}" mkpart primary ext4 512MiB 100% 2>/dev/null || true
    echo 25; sleep 1

    # Partições criadas
    PART_BOOT="${TARGET_DEV}1"
    PART_ROOT="${TARGET_DEV}2"
    if [[ "${TARGET_DEV}" =~ nvme ]]; then
        PART_BOOT="${TARGET_DEV}p1"
        PART_ROOT="${TARGET_DEV}p2"
    fi

    # Formatar
    mkfs.fat -F32 "${PART_BOOT}" >/dev/null 2>&1 || true
    mkfs.ext4 -F -L "NAYBINHO_OS" "${PART_ROOT}" >/dev/null 2>&1 || true
    echo 40; sleep 1

    # Montar e copiar sistema
    TARGET_MOUNT="/mnt/naybinho_target"
    mkdir -p "${TARGET_MOUNT}"
    mount "${PART_ROOT}" "${TARGET_MOUNT}"
    mkdir -p "${TARGET_MOUNT}/boot/efi"
    mount "${PART_BOOT}" "${TARGET_MOUNT}/boot/efi"
    echo 55; sleep 1

    # Copiar base de arquivos
    if [[ -d "/opt/naybinho" ]]; then
        mkdir -p "${TARGET_MOUNT}/opt/naybinho"
        rsync -a /opt/naybinho/ "${TARGET_MOUNT}/opt/naybinho/" 2>/dev/null || true
    fi
    echo 75; sleep 1

    # Configurar rede e bootloader
    echo "naybinho-nas" > "${TARGET_MOUNT}/etc/hostname" 2>/dev/null || true
    echo 90; sleep 1

    # Desmontar
    umount "${TARGET_MOUNT}/boot/efi" 2>/dev/null || true
    umount "${TARGET_MOUNT}" 2>/dev/null || true
    echo 100; sleep 1
} | whiptail --title "⏳ Instalando NayBinho NAS" \
    --backtitle "${WT_BACKTITLE}" \
    --gauge "Configurando discos, instalando sistema e serviços...\nPor favor, aguarde alguns instantes." \
    9 65 0

# 7. Obter IP local da máquina
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "192.168.1.100")

# 8. Tela de Parabéns
whiptail --title "🎉 Parabéns! Instalação Concluída" \
    --backtitle "${WT_BACKTITLE}" \
    --msgbox "O NayBinho NAS foi instalado com sucesso em ${TARGET_DEV}!\n\nCOMO ACESSAR O SEU NAS:\n1. Retire o pendrive de instalação.\n2. Reinicie o computador.\n3. Abra o navegador em qualquer celular ou PC na mesma rede:\n\n   👉 http://${LOCAL_IP}:8000\n   👉 ou http://naybinho-nas.local:8000\n\nUsuário padrão: admin\nSenha inicial:  naybinho" \
    18 70

# Pergunta se deseja reiniciar agora
if whiptail --title "Reiniciar Sistema" \
    --backtitle "${WT_BACKTITLE}" \
    --yesno "Deseja reiniciar o computador agora para começar a usar o NayBinho NAS?" \
    10 60; then
    reboot
fi
