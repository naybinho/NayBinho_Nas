#!/usr/bin/env bash
# =============================================================================
# NayBinho NAS — Setup e Gerenciamento de RAID via mdadm
# Menu interativo para criar, monitorar e gerenciar arrays RAID
# Suporta: RAID 0, 1, 5, 6, 10
# =============================================================================
set -euo pipefail

# ── Cores ─────────────────────────────────────────────────────────────────────
RED='\033[0;31m';    GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m';   CYAN='\033[0;36m';  BOLD='\033[1m'; NC='\033[0m'

# ── Utilitários ───────────────────────────────────────────────────────────────
log()    { echo -e "${GREEN}[✓]${NC} $*"; }
info()   { echo -e "${BLUE}[i]${NC} $*"; }
warn()   { echo -e "${YELLOW}[!]${NC} $*"; }
error()  { echo -e "${RED}[✗]${NC} $*" >&2; }
die()    { error "$*"; exit 1; }
confirm(){ read -rp "$(echo -e "${YELLOW}$* [s/N]:${NC} ")" ans; [[ "${ans,,}" == "s" ]]; }

# ── Verificar root e dependências ─────────────────────────────────────────────
check_requirements() {
    [[ $EUID -eq 0 ]] || die "Execute como root: sudo bash setup-raid.sh"
    command -v mdadm &>/dev/null || die "mdadm não encontrado. Instale: apt-get install mdadm"
    command -v lsblk &>/dev/null || die "lsblk não encontrado."
}

# ── Listar discos disponíveis ─────────────────────────────────────────────────
list_disks() {
    echo -e "\n${BOLD}${CYAN}═══ Discos Disponíveis ═══${NC}"
    echo ""
    lsblk -d -o NAME,SIZE,MODEL,SERIAL,TRAN,ROTA,MOUNTPOINT \
        --noheadings --sort NAME 2>/dev/null | \
        grep -v "^loop" | \
        awk '{printf "  /dev/%-8s  %-8s  %-20s  %s\n", $1, $2, $3, $4}'
    echo ""
}

# ── Listar arrays RAID existentes ─────────────────────────────────────────────
list_arrays() {
    echo -e "\n${BOLD}${CYAN}═══ Arrays RAID Existentes ═══${NC}"
    if [[ -f /proc/mdstat ]]; then
        cat /proc/mdstat
    else
        echo "  Nenhum array encontrado"
    fi
    echo ""

    # Detalhes com mdadm
    for md in /dev/md*; do
        if [[ -b "$md" ]]; then
            echo -e "${BOLD}Detalhes de $md:${NC}"
            mdadm --detail "$md" 2>/dev/null || true
            echo ""
        fi
    done
}

# ── Criar array RAID ──────────────────────────────────────────────────────────
create_raid() {
    echo -e "\n${BOLD}${CYAN}═══ Criar Novo Array RAID ═══${NC}\n"

    list_disks

    # Escolher nível RAID
    echo -e "${BOLD}Níveis RAID disponíveis:${NC}"
    echo "  0  - Striping (velocidade, SEM redundância) — mín. 2 discos"
    echo "  1  - Mirroring (redundância, 1 disco pode falhar) — mín. 2 discos"
    echo "  5  - Striping + paridade (1 disco pode falhar) — mín. 3 discos"
    echo "  6  - Striping + paridade dupla (2 discos podem falhar) — mín. 4 discos"
    echo "  10 - Striping + Mirroring (1 disco por sub-conjunto) — mín. 4 discos"
    echo ""
    read -rp "$(echo -e "${YELLOW}Escolha o nível RAID [0/1/5/6/10]:${NC} ")" raid_level

    case "$raid_level" in
        0) min_disks=2 ;;
        1) min_disks=2 ;;
        5) min_disks=3 ;;
        6) min_disks=4 ;;
        10) min_disks=4 ;;
        *) die "Nível RAID inválido: $raid_level" ;;
    esac

    # Nome do dispositivo MD
    read -rp "$(echo -e "${YELLOW}Nome do array (ex: md0, md1):${NC} ")" md_name
    md_name="${md_name#/dev/}"  # remover /dev/ se informado
    local md_device="/dev/${md_name}"

    if [[ -b "$md_device" ]]; then
        warn "Dispositivo $md_device já existe!"
        confirm "Deseja destruir e recriar?" || return
        mdadm --stop "$md_device" 2>/dev/null || true
        mdadm --remove "$md_device" 2>/dev/null || true
    fi

    # Selecionar discos
    echo -e "\n${BOLD}Informe os discos para o array RAID $raid_level (mínimo $min_disks):${NC}"
    echo -e "${YELLOW}Exemplo: /dev/sda /dev/sdb /dev/sdc${NC}"
    read -ra selected_disks -p "$(echo -e "${YELLOW}Discos:${NC} ")"

    if [[ ${#selected_disks[@]} -lt $min_disks ]]; then
        die "RAID $raid_level requer no mínimo $min_disks discos. Fornecido: ${#selected_disks[@]}"
    fi

    # Validar dispositivos
    for disk in "${selected_disks[@]}"; do
        [[ -b "$disk" ]] || die "Dispositivo $disk não encontrado ou não é um bloco"
    done

    # Exibir resumo e confirmar
    echo -e "\n${BOLD}Resumo do array a criar:${NC}"
    echo -e "  Dispositivo:  ${CYAN}${md_device}${NC}"
    echo -e "  Nível RAID:   ${CYAN}${raid_level}${NC}"
    echo -e "  Discos:       ${CYAN}${selected_disks[*]}${NC}"
    echo ""
    warn "ATENÇÃO: TODOS OS DADOS NOS DISCOS SERÃO DESTRUÍDOS!"
    confirm "Confirma a criação do array?" || { info "Cancelado."; return; }

    # Zerar superbloco dos discos
    info "Zerando superblocos antigos..."
    for disk in "${selected_disks[@]}"; do
        mdadm --zero-superblock "$disk" 2>/dev/null || true
        wipefs -a "$disk" 2>/dev/null || true
    done

    # Criar array
    info "Criando array RAID ${raid_level}..."
    mdadm --create \
        "$md_device" \
        --level="$raid_level" \
        --raid-devices="${#selected_disks[@]}" \
        --metadata=1.2 \
        "${selected_disks[@]}" << 'EOF'
yes
EOF

    # Aguardar sincronização inicial
    info "Array criado! Aguardando sincronização inicial..."
    sleep 2
    cat /proc/mdstat

    # Salvar configuração
    info "Salvando configuração mdadm..."
    mdadm --detail --scan >> /etc/mdadm/mdadm.conf
    update-initramfs -u 2>/dev/null || true

    # Formatar e montar
    echo ""
    read -rp "$(echo -e "${YELLOW}Ponto de montagem (ex: /mnt/raid, deixe em branco para pular):${NC} ")" mount_point

    if [[ -n "$mount_point" ]]; then
        echo -e "\n${BOLD}Sistema de arquivos:${NC}"
        echo "  1) ext4 (recomendado — estável, amplamente suportado)"
        echo "  2) xfs  (melhor para arquivos grandes)"
        echo "  3) btrfs (snapshots, compressão)"
        read -rp "$(echo -e "${YELLOW}Escolha [1/2/3]:${NC} ")" fs_choice

        case "$fs_choice" in
            1) mkfs.ext4 -F -L "NayBinho-RAID${raid_level}" "$md_device" ;;
            2) mkfs.xfs -f -L "NayBinho-RAID${raid_level}" "$md_device" ;;
            3) mkfs.btrfs -f -L "NayBinho-RAID${raid_level}" "$md_device" ;;
            *) warn "Opção inválida, pulando formatação" ;;
        esac

        mkdir -p "$mount_point"
        mount "$md_device" "$mount_point"

        # Adicionar ao fstab
        local uuid
        uuid=$(blkid -s UUID -o value "$md_device")
        echo "UUID=${uuid}  ${mount_point}  ext4  defaults,nofail  0  2" >> /etc/fstab
        log "Array montado em $mount_point e adicionado ao fstab"
    fi

    log "Array RAID ${raid_level} criado com sucesso em ${md_device}!"
    mdadm --detail "$md_device"
}

# ── Verificar saúde dos arrays ────────────────────────────────────────────────
check_health() {
    echo -e "\n${BOLD}${CYAN}═══ Verificação de Saúde dos Arrays RAID ═══${NC}\n"

    if ! ls /dev/md* &>/dev/null 2>&1; then
        info "Nenhum array RAID ativo encontrado."
        return
    fi

    local has_problem=false

    for md in /dev/md*; do
        [[ -b "$md" ]] || continue
        echo -e "${BOLD}═══ $md ═══${NC}"
        local state
        state=$(mdadm --detail "$md" 2>/dev/null | grep "State :" | awk '{print $3}')

        case "$state" in
            clean)
                echo -e "  Estado: ${GREEN}✓ Saudável (clean)${NC}"
                ;;
            active)
                echo -e "  Estado: ${GREEN}✓ Ativo${NC}"
                ;;
            *degraded*)
                echo -e "  Estado: ${RED}✗ DEGRADADO — Requer atenção!${NC}"
                has_problem=true
                ;;
            *recovering*|*resync*)
                local progress
                progress=$(cat /proc/mdstat | grep -A2 "${md#/dev/}" | grep "%" | grep -oP '\d+\.\d+%' | head -1)
                echo -e "  Estado: ${YELLOW}↻ Sincronizando... $progress${NC}"
                ;;
            *failed*)
                echo -e "  Estado: ${RED}✗ FALHOU — CRÍTICO!${NC}"
                has_problem=true
                ;;
            *)
                echo -e "  Estado: ${YELLOW}? $state${NC}"
                ;;
        esac

        mdadm --detail "$md" | grep -E "Raid Level|Array Size|Used Dev Size|Raid Devices|Total Devices|Active Devices|Working Devices|Failed Devices|Spare Devices" | \
            sed 's/^/  /'
        echo ""
    done

    if $has_problem; then
        warn "ATENÇÃO: Um ou mais arrays apresentam problemas!"
    else
        log "Todos os arrays estão saudáveis"
    fi
}

# ── Adicionar disco de spare ──────────────────────────────────────────────────
add_spare() {
    echo -e "\n${BOLD}${CYAN}═══ Adicionar Disco Spare ═══${NC}\n"
    list_arrays
    list_disks

    read -rp "$(echo -e "${YELLOW}Array RAID (ex: /dev/md0):${NC} ")" md_device
    read -rp "$(echo -e "${YELLOW}Disco spare (ex: /dev/sdd):${NC} ")" spare_disk

    [[ -b "$md_device" ]] || die "Dispositivo $md_device não encontrado"
    [[ -b "$spare_disk" ]] || die "Disco $spare_disk não encontrado"

    confirm "Adicionar $spare_disk como spare em $md_device?" || return

    mdadm --add "$md_device" "$spare_disk"
    log "$spare_disk adicionado como spare em $md_device"
}

# ── Remover array RAID ────────────────────────────────────────────────────────
remove_array() {
    echo -e "\n${BOLD}${CYAN}═══ Remover Array RAID ═══${NC}\n"
    list_arrays

    read -rp "$(echo -e "${YELLOW}Array a remover (ex: /dev/md0):${NC} ")" md_device
    [[ -b "$md_device" ]] || die "Dispositivo $md_device não encontrado"

    warn "ATENÇÃO: TODOS OS DADOS DO ARRAY SERÃO PERDIDOS!"
    confirm "Confirma remoção de $md_device?" || { info "Cancelado."; return; }

    # Desmontar se montado
    umount "$md_device" 2>/dev/null || true

    # Parar array
    mdadm --stop "$md_device"

    # Zerar superblocos
    local members
    members=$(mdadm --detail "$md_device" 2>/dev/null | grep '/dev/' | awk '{print $7}' || true)
    for disk in $members; do
        mdadm --zero-superblock "$disk" 2>/dev/null || true
    done

    # Remover do mdadm.conf
    sed -i "/${md_device//\//\\/}/d" /etc/mdadm/mdadm.conf 2>/dev/null || true

    update-initramfs -u 2>/dev/null || true
    log "Array $md_device removido"
}

# ── Status do progresso de sync ───────────────────────────────────────────────
watch_sync() {
    echo -e "\n${BOLD}${CYAN}═══ Monitorar Sincronização (Ctrl+C para sair) ═══${NC}\n"
    while true; do
        clear
        echo -e "${BOLD}$(date) — Status RAID${NC}"
        cat /proc/mdstat
        sleep 3
    done
}

# ── Menu principal ────────────────────────────────────────────────────────────
main_menu() {
    while true; do
        echo ""
        echo -e "${BOLD}${CYAN}╔═══════════════════════════════════════╗${NC}"
        echo -e "${BOLD}${CYAN}║      NayBinho NAS — RAID Manager      ║${NC}"
        echo -e "${BOLD}${CYAN}╠═══════════════════════════════════════╣${NC}"
        echo -e "${CYAN}║  1) Listar discos disponíveis          ║${NC}"
        echo -e "${CYAN}║  2) Listar arrays RAID existentes      ║${NC}"
        echo -e "${CYAN}║  3) Criar novo array RAID              ║${NC}"
        echo -e "${CYAN}║  4) Verificar saúde dos arrays         ║${NC}"
        echo -e "${CYAN}║  5) Adicionar disco spare              ║${NC}"
        echo -e "${CYAN}║  6) Remover array RAID                 ║${NC}"
        echo -e "${CYAN}║  7) Monitorar sincronização            ║${NC}"
        echo -e "${CYAN}║  0) Sair                               ║${NC}"
        echo -e "${BOLD}${CYAN}╚═══════════════════════════════════════╝${NC}"
        echo ""
        read -rp "$(echo -e "${YELLOW}Escolha uma opção:${NC} ")" choice

        case "$choice" in
            1) list_disks ;;
            2) list_arrays ;;
            3) create_raid ;;
            4) check_health ;;
            5) add_spare ;;
            6) remove_array ;;
            7) watch_sync ;;
            0) info "Saindo..."; exit 0 ;;
            *) warn "Opção inválida: $choice" ;;
        esac
    done
}

# ── Entry point ───────────────────────────────────────────────────────────────
check_requirements
main_menu
