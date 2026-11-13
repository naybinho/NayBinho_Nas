# 🌐 Guia de Configuração de Rede — NayBinho NAS

> **Versão:** 1.0.0 | **Base:** Ubuntu 26.04.1 LTS (Netplan / systemd-networkd)

---

## Índice

1. [Visão Geral de Rede](#1-visão-geral-de-rede)
2. [Configuração de IP (DHCP e Estático)](#2-configuração-de-ip-dhcp-e-estático)
3. [Configuração de DNS e Gateway](#3-configuração-de-dns-e-gateway)
4. [VLANs (Redes Locais Virtuais)](#4-vlans-redes-locais-virtuais)
5. [Bonding / Link Aggregation (LACP)](#5-bonding--link-aggregation-lacp)
6. [Bridges (Pontes Virtuais para Docker/VMs)](#6-bridges-pontes-virtuais-para-dockervms)
7. [Wi-Fi (Redes Sem Fio)](#7-wi-fi-redes-sem-fio)
8. [Configuração via Netplan (CLI)](#8-configuração-via-netplan-cli)
9. [Troubleshooting e Diagnóstico de Rede](#9-troubleshooting-e-diagnóstico-de-rede)

---

## 1. Visão Geral de Rede

O NayBinho NAS utiliza **Netplan** com backend `systemd-networkd` para gerenciamento avançado e determinístico de interfaces de rede.

A interface gráfica de gerenciamento permite configurar interfaces físicas, virtuais, bonding e VLANs sem necessidade de editar arquivos YAML manualmente, aplicando alterações de forma segura com rollback automático em caso de perda de conectividade.

### Portas Padrão do Sistema

| Porta / Protocolo | Serviço | Descrição |
|---|---|---|
| `8080/tcp` | Web UI (HTTP) | Painel de controle web |
| `8443/tcp` | Web UI (HTTPS) | Painel seguro com SSL/TLS |
| `22/tcp` | SSH | Acesso terminal remoto |
| `445/tcp` | SMB / CIFS | Compartilhamento de arquivos Windows |
| `139/tcp` | NetBIOS / SMB | Resolução legada SMB |
| `2049/tcp,udp` | NFS v3/v4 | Compartilhamento Linux/UNIX |
| `111/tcp,udp` | rpcbind / Portmapper | Requisito para NFS |
| `5353/udp` | mDNS / Avahi | Descoberta zero-config (`naybinho-nas.local`) |

---

## 2. Configuração de IP (DHCP e Estático)

### 2.1 Pela Interface Web

1. Acesse **Configurações → Rede → Interfaces**.
2. Clique no botão de edição (ícone lápis) ao lado da interface desejada (ex: `eth0` ou `enp3s0`).
3. No campo **Modo de Endereçamento**, selecione:
   - **DHCP:** O roteador distribui IP, máscara, gateway e DNS automaticamente.
   - **Estático (Recomendado para servidores):** Preencha os campos:
     - **Endereço IPv4:** Ex: `192.168.1.100`
     - **Máscara de Sub-rede / CIDR:** Ex: `255.255.255.0` (ou `/24`)
     - **Gateway:** IP do roteador (ex: `192.168.1.1`)
     - **Servidores DNS:** Ex: `1.1.1.1, 8.8.8.8`
4. Clique em **Testar Conectividade**. Uma contagem regressiva de 30 segundos começará; se a conexão falhar ou não for confirmada, as alterações são revertidas automaticamente.
5. Clique em **Salvar e Aplicar**.

---

## 3. Configuração de DNS e Gateway

Configurar servidores DNS rápidos e confiáveis garante que a loja de aplicativos, atualizações de sistema e notificações funcionem perfeitamente.

### Provedores DNS Recomendados

- **Cloudflare:** `1.1.1.1`, `1.0.0.1` (baixa latência e foco em privacidade)
- **Google:** `8.8.8.8`, `8.8.4.4`
- **Quad9:** `9.9.9.9` (bloqueio de domínios maliciosos)
- **Pi-hole / AdGuard Home local:** IP do seu resolvedor DNS interno

---

## 4. VLANs (Redes Locais Virtuais)

As VLANs (IEEE 802.1Q) permitem isolar o tráfego do NAS em redes lógicas diferentes (ex: VLAN de Gestão, VLAN de Mídia/Streaming, VLAN de Câmeras/IoT).

### 4.1 Criando uma VLAN via Web UI

1. Vá em **Configurações → Rede → "+ Adicionar Interface" → "VLAN"**.
2. Parâmetros:
   - **Nome da Interface:** Ex: `vlan10` ou `enp3s0.10`
   - **Interface Pai (Física):** Ex: `enp3s0`
   - **ID da VLAN (Tag 802.1Q):** Número de 1 a 4094 (ex: `10`)
   - **Endereçamento:** DHCP ou IP Estático dedicado a essa sub-rede
3. Clique em **Criar e Aplicar**.

### 4.2 Exemplo de Topologia com VLAN

```
             [ Switch Gerenciável (Trunk 802.1Q) ]
                           │
                 [ Cabo de Rede Único ]
                           │
               [ NayBinho NAS (enp3s0) ]
              ┌────────────┴────────────┐
       enp3s0.10 (VLAN 10)       enp3s0.20 (VLAN 20)
       Subnet: 10.10.10.0/24     Subnet: 10.20.20.0/24
       Uso: Gestão / Admin       Uso: Mídia (Jellyfin/Plex)
```

---

## 5. Bonding / Link Aggregation (LACP)

O recurso de Bonding combina duas ou mais placas de rede físicas em uma única interface lógica (`bond0`), proporcionando **redundância (failover)** e **aumento de largura de banda agregada**.

### 5.1 Modos de Bonding Suportados

| Modo | Nome Técnico | Requisito de Switch | Benefício Principal |
|---|---|---|---|
| **Mode 1** | `active-backup` | Qualquer switch não gerenciável | Alta tolerância a falhas (cabo/porta) |
| **Mode 4** | `802.3ad` (LACP) | Switch gerenciável com suporte LACP | Alta performance agregada e failover |
| **Mode 0** | `balance-rr` | Switch compatível / estático | Round-robin de pacotes |
| **Mode 6** | `balance-alb` | Qualquer switch | Balanceamento adaptativo de carga |

### 5.2 Criando um Bond via Web UI

1. Vá em **Configurações → Rede → "+ Adicionar Interface" → "Bond (Agregação)"**.
2. Defina:
   - **Nome:** `bond0`
   - **Modo:** `802.3ad (LACP)` ou `Active-Backup`
   - **Interfaces Escravas (Slaves):** Marque `enp3s0` e `enp4s0`
   - **Monitoramento:** MII (intervalo de 100ms)
   - **Hash de Transmissão (para LACP):** `layer2+3` (recomendado)
   - **Configuração IP do Bond:** Atribua o IP estático ou DHCP ao `bond0`
3. Clique em **Salvar e Aplicar**.

---

## 6. Bridges (Pontes Virtuais para Docker/VMs)

Uma Bridge Linux (`br0`) atua como um switch virtual conectado à interface física. É essencial quando containers ou máquinas virtuais precisam ter endereços IP próprios na mesma sub-rede da sua rede local (LAN).

### 6.1 Criando uma Bridge

1. Vá em **Configurações → Rede → "+ Adicionar Interface" → "Bridge"**.
2. Nome: `br0`.
3. Interface física membro: `enp3s0`.
4. Transfira a configuração de IP da interface física para a `br0`.
5. Salve e aplique. Containers Docker com rede macvlan/ipvlan poderão se ancorar diretamente na `br0`.

---

## 7. Wi-Fi (Redes Sem Fio)

> ⚠️ **Aviso de Desempenho:** Para um servidor NAS, conexão cabeada Gigabit (ou 2.5GbE/10GbE) é fortemente recomendada. Wi-Fi deve ser utilizado apenas como contingência ou em cenários laboratoriais específicos.

### Conexão via Web UI

1. Em **Configurações → Rede → Wi-Fi**, ative o adaptador sem fio.
2. Clique em **Buscar Redes**.
3. Selecione o SSID, informe a senha (WPA2/WPA3 Personal) e clique em **Conectar**.

---

## 8. Configuração via Netplan (CLI)

Para administradores que preferem a linha de comando, os arquivos de rede ficam armazenados em `/etc/netplan/01-naybinho-network.yaml`.

### Exemplo Completo de Configuração Netplan

```yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    enp3s0:
      dhcp4: false
    enp4s0:
      dhcp4: false
  bonds:
    bond0:
      interfaces:
        - enp3s0
        - enp4s0
      parameters:
        mode: 802.3ad
        lacp-rate: fast
        mii-monitor-interval: 100
        transmit-hash-policy: layer2+3
      addresses:
        - 192.168.1.150/24
      routes:
        - to: default
          via: 192.168.1.1
      nameservers:
        addresses:
          - 1.1.1.1
          - 8.8.8.8
  vlans:
    vlan30:
      id: 30
      link: bond0
      addresses:
        - 10.30.0.10/24
```

### Aplicando Alterações com Segurança

```bash
# Valida e aplica com timeout de reversão automática caso você perca o SSH
sudo netplan try

# Aplica diretamente
sudo netplan apply
```

---

## 9. Troubleshooting e Diagnóstico de Rede

### Comandos Rápidos de Terminal

```bash
# Verificar status e endereços de todas as interfaces
ip -c addr

# Verificar tabela de rotas padrão
ip route show

# Testar conectividade e resolução de nomes
ping -c 4 1.1.1.1
ping -c 4 google.com

# Status do bonding
cat /proc/net/bonding/bond0

# Verificar portas abertas em escuta
sudo ss -tulpn

# Monitorar tráfego em tempo real por interface
sudo iftop -i enp3s0
```

### Problemas Comuns e Soluções

1. **IP duplicado na rede:**
   - Sintoma: Conexão instável, desconexões frequentes do painel web.
   - Solução: Reserve o endereço MAC do NAS nas configurações DHCP do seu roteador (DHCP Static Lease).

2. **Perda de acesso após ativar LACP:**
   - Causa: O switch físico ainda não está configurado em modo LACP ou as portas não pertencem ao mesmo grupo LAG.
   - Solução: Use `active-backup` até configurar a porta no switch físico.

3. **Velocidade limitada a 100 Mbps em vez de 1 Gbps:**
   - Causa: Cabo de rede defeituoso (Cat5e/Cat6 partido) ou pinagem inadequada.
   - Verifique com: `sudo ethtool enp3s0 | grep Speed`
