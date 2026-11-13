#!/usr/bin/env bash
# =============================================================================
# NayBinho NAS — Assistente de Instalação Guiado (TUI Moderno v2)
# =============================================================================
# Totalmente customizado: sem referências ao Ubuntu ou Subiquity.
# Paleta Cyberpunk Dark Glass / Neon Cyan.
# =============================================================================
set -uo pipefail

export TERM=xterm-256color
export WT_BACKTITLE="  NayBinho NAS v1.0.0 — Home Lab OS  |  Instalador Oficial"

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
# 2. Garantir que whiptail está disponível
# ---------------------------------------------------------------------------
if ! command -v whiptail &>/dev/null; then
    echo "Instalando dependências do instalador..."
    apt-get update -qq 2>/dev/null
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq whiptail newt 2>/dev/null || true
fi
if ! command -v rsync &>/dev/null; then
    DEBIAN_FRONTEND=noninteractive apt-get install -y -qq rsync 2>/dev/null || true
fi

# ---------------------------------------------------------------------------
# 3. Tela de Splash ASCII (NayBinho NAS)
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
sleep 2

# ---------------------------------------------------------------------------
# 4. Tela de Boas-Vindas
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
  ✔  Instala e configura o sistema completo com GRUB\n\
  ✔  Ativa o painel Web automaticamente após reiniciar\n\
\n\
Pressione ENTER para continuar ou ESC para cancelar." \
    20 72

# ---------------------------------------------------------------------------
# 5. Detectar discos disponíveis (exclui pendrive de boot e loop devices)
# ---------------------------------------------------------------------------
BOOT_DEV=""
# Detectar dispositivo de boot montado em /cdrom ou /isodevice
for mpoint in /cdrom /isodevice /media/cdrom; do
    if mountpoint -q "${mpoint}" 2>/dev/null; then
        BOOT_DEV=$(lsblk -no PKNAME "$(findmnt -n -o SOURCE ${mpoint} 2>/dev/null)" 2>/dev/null || true)
        break
    fi
done
# Fallback: detectar via /proc/mounts
if [[ -z "${BOOT_DEV}" ]]; then
    BOOT_DEV=$(awk '/\/cdrom|\/isodevice/{print $1}' /proc/mounts 2>/dev/null | \
               sed 's|/dev/||;s|[0-9]*$||;s|p[0-9]*$||' | head -1 || true)
fi

DISKS_MENU=()
while IFS= read -r line; do
    name=$(echo "$line" | awk '{print $1}')
    size=$(echo "$line" | awk '{print $2}')
    model=$(echo "$line" | awk '{$1=$2=$3=$4=""; print $0}' | sed 's/^ *//')
    tran=$(echo "$line" | awk '{print $3}')
    rota=$(echo "$line" | awk '{print $4}')

    # Pular loop, ram, sr*, zram e o dispositivo de boot
    [[ "${name}" =~ ^loop ]] && continue
    [[ "${name}" =~ ^ram  ]] && continue
    [[ "${name}" =~ ^sr   ]] && continue
    [[ "${name}" =~ ^zram ]] && continue
    [[ "${name}" == "${BOOT_DEV}" ]] && continue

    # Montar descrição amigável
    if [[ "${rota}" == "0" ]]; then
        tipo="SSD/NVMe"
    else
        tipo="HD (Rotativo)"
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
# 6. Menu de seleção de disco
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
# 7. Confirmação com alerta claro de formatação
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
# 8. Executar instalação com barra de progresso
# ---------------------------------------------------------------------------
perform_install() {
    # Passo 1: Limpar disco
    echo 5
    echo "XXX"
    echo "5"
    echo "[ 1/9 ] Preparando o disco ${TARGET_DEV}..."
    echo "XXX"
    wipefs -a "${TARGET_DEV}" >/dev/null 2>&1 || true
    sleep 1

    # Passo 2: Criar tabela de partições GPT
    echo 12
    echo "XXX"
    echo "12"
    echo "[ 2/9 ] Criando tabela de partições GPT..."
    echo "XXX"
    parted -s "${TARGET_DEV}" mklabel gpt  2>/dev/null || true
    # Partição EFI (512 MB)
    parted -s "${TARGET_DEV}" mkpart "EFI"          fat32  1MiB  513MiB  2>/dev/null || true
    parted -s "${TARGET_DEV}" set 1 esp on           2>/dev/null || true
    # Partição raiz do sistema
    parted -s "${TARGET_DEV}" mkpart "NAYBINHO_ROOT" ext4   513MiB 100%   2>/dev/null || true
    sleep 1

    # Passo 3: Detectar nomes das partições (NVMe usa p1/p2)
    echo 20
    echo "XXX"
    echo "20"
    echo "[ 3/9 ] Detectando partições criadas..."
    echo "XXX"
    sleep 1
    partprobe "${TARGET_DEV}" 2>/dev/null || true
    sleep 2

    if [[ "${TARGET_DEV}" =~ nvme|mmcblk ]]; then
        PART_BOOT="${TARGET_DEV}p1"
        PART_ROOT="${TARGET_DEV}p2"
    else
        PART_BOOT="${TARGET_DEV}1"
        PART_ROOT="${TARGET_DEV}2"
    fi

    # Passo 4: Formatar partições
    echo 28
    echo "XXX"
    echo "28"
    echo "[ 4/9 ] Formatando partições (FAT32 EFI + EXT4 Sistema)..."
    echo "XXX"
    mkfs.fat -F32 -n "NAYBINHO_EFI" "${PART_BOOT}" >/dev/null 2>&1 || true
    mkfs.ext4 -F -L "NAYBINHO_OS"  "${PART_ROOT}" >/dev/null 2>&1 || true
    sleep 1

    # Passo 5: Montar partições
    echo 35
    echo "XXX"
    echo "35"
    echo "[ 5/9 ] Montando partições de destino..."
    echo "XXX"
    TARGET_MOUNT="/mnt/naybinho_target"
    umount -l "${TARGET_MOUNT}" 2>/dev/null || true
    rm -rf "${TARGET_MOUNT}"
    mkdir -p "${TARGET_MOUNT}"
    mount "${PART_ROOT}" "${TARGET_MOUNT}" || {
        echo "ERRO: Não foi possível montar ${PART_ROOT}"
        exit 1
    }
    mkdir -p "${TARGET_MOUNT}/boot/efi"
    mount "${PART_BOOT}" "${TARGET_MOUNT}/boot/efi" || true
    sleep 1

    # Passo 6: Copiar sistema ao vivo para o disco
    echo 42
    echo "XXX"
    echo "42"
    echo "[ 6/9 ] Copiando sistema NayBinho NAS para o disco..."
    echo "        (Pode demorar alguns minutos)"
    echo "XXX"
    rsync -aAX \
        --exclude={"/dev/*","/proc/*","/sys/*","/tmp/*","/run/*","/mnt/*","/media/*","/lost+found","/cdrom/*","/isodevice/*"} \
        / "${TARGET_MOUNT}/" 2>/dev/null || true

    # Passo 7: Configurar fstab
    echo 72
    echo "XXX"
    echo "72"
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

    # Hostname
    echo "naybinho-nas" > "${TARGET_MOUNT}/etc/hostname"
    sleep 1

    # Passo 8: Instalar bootloader GRUB
    echo 82
    echo "XXX"
    echo "82"
    echo "[ 8/9 ] Instalando bootloader GRUB (UEFI + BIOS)..."
    echo "XXX"
    # Montar bind mounts para chroot
    for dir in dev dev/pts proc sys run; do
        mkdir -p "${TARGET_MOUNT}/${dir}"
        mount --bind "/${dir}" "${TARGET_MOUNT}/${dir}" 2>/dev/null || true
    done

    # Copiar tema e plano de fundo GRUB para o disco instalado
    if [[ -d /boot/grub/themes/naybinho ]]; then
        mkdir -p "${TARGET_MOUNT}/boot/grub/themes"
        cp -r /boot/grub/themes/naybinho "${TARGET_MOUNT}/boot/grub/themes/" 2>/dev/null || true
    fi
    if [[ -f /boot/grub/background.jpg ]]; then
        cp /boot/grub/background.jpg "${TARGET_MOUNT}/boot/grub/background.jpg" 2>/dev/null || true
    fi

    # Instalar GRUB UEFI e BIOS
    chroot "${TARGET_MOUNT}" grub-install \
        --target=x86_64-efi \
        --efi-directory=/boot/efi \
        --bootloader-id=NayBinhoNAS \
        --recheck 2>/dev/null || true
    chroot "${TARGET_MOUNT}" grub-install \
        --target=i386-pc \
        "${TARGET_DEV}" \
        --recheck 2>/dev/null || true
    chroot "${TARGET_MOUNT}" update-grub 2>/dev/null || true

    # Desabilitar instalador no sistema instalado e ativar serviços NAS
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
    echo "[ 9/9 ] Finalizando e desmontando discos..."
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
    --gauge "\nInstalando o sistema. Por favor, aguarde...\n" \
    10 72 0

# ---------------------------------------------------------------------------
# 9. Obter IP local
# ---------------------------------------------------------------------------
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "192.168.X.X")
[[ -z "${LOCAL_IP}" ]] && LOCAL_IP="192.168.X.X"

# ---------------------------------------------------------------------------
# 10. Tela de sucesso com instruções de acesso
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
# 11. Oferecer reinicialização
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
