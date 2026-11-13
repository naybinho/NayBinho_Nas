# 📦 Guia de Instalação — NayBinho NAS

> **Versão:** 1.0.0 | **Base:** Ubuntu 26.04.1 LTS

---

## Índice

1. [Requisitos de Hardware](#1-requisitos-de-hardware)
2. [Download da ISO](#2-download-da-iso)
3. [Criação do USB Bootável](#3-criação-do-usb-bootável)
4. [Instalação Passo a Passo](#4-instalação-passo-a-passo)
5. [Primeiro Acesso à Interface Web](#5-primeiro-acesso-à-interface-web)
6. [Configuração Inicial (Wizard)](#6-configuração-inicial-wizard)
7. [Próximos Passos](#7-próximos-passos)

---

## 1. Requisitos de Hardware

### Mínimo (Funcional)

| Componente | Requisito Mínimo |
|---|---|
| **CPU** | x86-64, 2 núcleos, 1.5 GHz |
| **RAM** | 4 GB DDR4 |
| **Disco do Sistema** | 32 GB SSD/HDD (dedicado) |
| **Discos de Dados** | 1 ou mais HDD/SSD |
| **Rede** | 1x Gigabit Ethernet (1GbE) |
| **USB** | Apenas para instalação (1 porta) |

### Recomendado (Melhor Experiência)

| Componente | Recomendado |
|---|---|
| **CPU** | x86-64, 4+ núcleos, 2.4 GHz (Intel N100, Ryzen 5, Xeon E3) |
| **RAM** | 8–16 GB DDR4/DDR5 |
| **Disco do Sistema** | 64 GB+ SSD M.2 ou SATA (dedicado, separado dos dados) |
| **Discos de Dados** | 2–8 HDD/SSD (para RAID) |
| **Rede** | 2x Gigabit Ethernet (para bonding/redundância) |
| **Fonte** | Com suporte a hot-swap (servidores) |

### Notas sobre Hardware

- **ZFS:** Recomenda 1 GB de RAM por 1 TB de armazenamento para melhor performance.
- **RAID 5/6:** Mínimo de 3 e 4 discos respectivamente.
- **Virtualização:** NayBinho NAS pode ser instalado em VMs (VMware, Proxmox, VirtualBox) para testes.
- **UEFI vs BIOS:** Ambos são suportados. UEFI é preferido para hardware moderno.

---

## 2. Download da ISO

### Download Oficial

Acesse o repositório oficial e baixe a versão mais recente:

```
https://github.com/naybinho/naybinho-nas/releases/latest
```

Arquivo: `naybinho-nas-1.0.0-amd64.iso`

### Verificação de Integridade

Sempre verifique o hash SHA256 antes de instalar:

```bash
# Linux / macOS
sha256sum naybinho-nas-1.0.0-amd64.iso

# Windows (PowerShell)
Get-FileHash naybinho-nas-1.0.0-amd64.iso -Algorithm SHA256
```

Compare o resultado com o arquivo `SHA256SUMS` disponível na página de releases.

---

## 3. Criação do USB Bootável

### Usando Rufus (Windows) — Recomendado

1. Baixe o **Rufus** em [https://rufus.ie](https://rufus.ie)
2. Insira o pendrive USB (mínimo 8 GB — todos os dados serão apagados)
3. Abra o Rufus como administrador
4. Configure:
   - **Dispositivo:** Selecione o seu pendrive
   - **Seleção de boot:** Clique em "SELECIONAR" e escolha `naybinho-nas-1.0.0-amd64.iso`
   - **Esquema de partição:** GPT (para UEFI) ou MBR (para BIOS legado)
   - **Sistema de destino:** UEFI (non CSM) ou BIOS/UEFI
   - **Sistema de arquivos:** FAT32
5. Clique em **INICIAR**
6. Quando perguntado sobre o modo de escrita, selecione **"Escrever em modo imagem ISO"**
7. Aguarde a conclusão

### Usando Balena Etcher (Windows / macOS / Linux)

1. Baixe o **Balena Etcher** em [https://etcher.balena.io](https://etcher.balena.io)
2. Insira o pendrive USB
3. Abra o Balena Etcher
4. Clique em **"Flash from file"** → selecione a ISO
5. Clique em **"Select target"** → selecione o pendrive
6. Clique em **"Flash!"**
7. Aguarde a conclusão e confirmação de verificação

### Usando `dd` (Linux / macOS)

```bash
# Identifique o dispositivo USB (cuidado para não usar o disco errado!)
lsblk

# Grave a ISO (substitua /dev/sdX pelo seu dispositivo)
sudo dd if=naybinho-nas-1.0.0-amd64.iso of=/dev/sdX bs=4M status=progress conv=fdatasync
```

---

## 4. Instalação Passo a Passo

### 4.1 — Boot pelo USB

1. Insira o pendrive USB no servidor/PC onde será instalado o NayBinho NAS
2. Ligue o equipamento e acesse o menu de boot:
   - **Dell:** F12
   - **HP:** F9 ou ESC
   - **ASUS/MSI:** F8 ou Del
   - **Lenovo:** F12 ou Enter
   - **Intel NUC:** F10
3. Selecione o pendrive USB na lista de dispositivos de boot
4. Aguarde o carregamento do menu do NayBinho NAS

### 4.2 — Menu de Boot

Você verá o menu GRUB do NayBinho NAS com as opções:

```
┌─────────────────────────────────────┐
│   🏠 NayBinho NAS v1.0.0            │
├─────────────────────────────────────┤
│ ▶  Instalar NayBinho NAS            │
│    Testar sem instalar (Live)       │
│    Verificar mídia e instalar       │
│    Modo de recuperação              │
└─────────────────────────────────────┘
```

Selecione **"Instalar NayBinho NAS"** e pressione Enter.

### 4.3 — Assistente de Instalação

#### Passo 1: Idioma e Localização
- Selecione o idioma: **Português (Brasil)**
- Fuso horário: **America/São_Paulo** (ou o seu)
- Layout de teclado: **Português (Brasil, sem teclas mortas)**

#### Passo 2: Configuração de Rede
- O instalador detectará automaticamente as interfaces de rede
- Escolha **DHCP** para configuração automática (pode alterar depois)
- Ou configure **IP Estático** manualmente

#### Passo 3: Disco do Sistema ⚠️

> **ATENÇÃO:** O disco do sistema será completamente formatado. Certifique-se de selecionar o disco correto!

- Selecione o disco destinado ao **sistema** (não os discos de dados)
- Recomendado: SSD dedicado de no mínimo 32 GB
- Esquema de particionamento padrão:
  ```
  /boot/efi  →  512 MB  (EFI, apenas UEFI)
  /boot      →  1 GB    (ext4)
  swap       →  4 GB    (swap)
  /          →  restante (ext4)
  ```

#### Passo 4: Usuário Administrador
- **Nome completo:** Seu nome (ex: "Administrador NAS")
- **Nome de usuário:** `admin` (padrão)
- **Senha:** Defina uma senha forte (mínimo 8 caracteres)
- **Hostname:** Nome do servidor (ex: `naybinho-nas`, sem espaços)

#### Passo 5: Confirmação e Instalação

Revise as configurações e clique em **"Instalar"**. A instalação leva aproximadamente **5–15 minutos** dependendo do hardware.

Progresso da instalação:
```
[████████████████████░░░░░░░░░░] 65%
Copiando arquivos do sistema...
```

#### Passo 6: Reinicialização

Após a conclusão:
1. Clique em **"Reiniciar agora"**
2. **Remova o pendrive USB** quando solicitado
3. O sistema reiniciará e realizará configurações finais (3–5 minutos na primeira vez)

---

## 5. Primeiro Acesso à Interface Web

### Descobrindo o IP do Sistema

Após o boot, o NayBinho NAS exibirá no console/tela:

```
╔══════════════════════════════════════════╗
║          NayBinho NAS v1.0.0             ║
║                                          ║
║  Acesse a interface web em:              ║
║  → http://192.168.1.100:8080             ║
║  → http://naybinho-nas.local:8080        ║
║                                          ║
║  Ou via SSH: ssh admin@192.168.1.100     ║
╚══════════════════════════════════════════╝
```

### Acessando pelo Navegador

1. Abra seu navegador (Chrome, Firefox, Edge)
2. Digite o endereço exibido no console, ex: `http://192.168.1.100:8080`
3. Você será redirecionado automaticamente para o **Wizard de Configuração Inicial**

> **Dica:** Use `http://naybinho-nas.local:8080` se o seu roteador suportar mDNS (a maioria dos roteadores modernos suporta).

---

## 6. Configuração Inicial (Wizard)

O Wizard de Configuração Inicial aparece automaticamente no primeiro acesso e guia você pelos seguintes passos:

### Passo 1: Bem-vindo
- Tela de boas-vindas com visão geral do sistema
- Clique em **"Começar Configuração"**

### Passo 2: Definir Hostname
- Nome do servidor na rede (ex: `naybinho-nas`, `meu-nas`, `homelab`)
- Deve conter apenas letras, números e hífens

### Passo 3: Senha do Administrador
- Defina a senha do usuário `admin` para a interface web
- **Mínimo:** 8 caracteres
- **Recomendado:** 12+ caracteres com maiúsculas, minúsculas, números e símbolos

### Passo 4: Configuração de Rede
- Escolha a interface de rede principal
- Configure DHCP ou IP estático (IP, máscara, gateway, DNS)

### Passo 5: Fuso Horário
- Selecione o fuso horário correto para logs e agendamentos precisos

### Passo 6: Configuração NTP
- Servidor de tempo (padrão: `pool.ntp.org`)
- O sistema sincronizará o relógio automaticamente

### Passo 7: Resumo e Finalização
- Revise todas as configurações
- Clique em **"Aplicar e Finalizar"**
- O sistema aplicará as configurações (30–60 segundos)
- Você será redirecionado ao **Dashboard principal**

---

## 7. Próximos Passos

Após a instalação e configuração inicial, consulte:

| Guia | Descrição |
|---|---|
| [USER_GUIDE.md](USER_GUIDE.md) | Manual completo de uso da interface |
| [NETWORK_GUIDE.md](NETWORK_GUIDE.md) | Configuração de rede avançada |
| [SHARING_GUIDE.md](SHARING_GUIDE.md) | Configurar compartilhamentos SMB/NFS |
| [ADMIN_GUIDE.md](ADMIN_GUIDE.md) | Backup, restauração e troubleshooting |
| [FAQ.md](FAQ.md) | Perguntas frequentes |

---

## Suporte

- **GitHub Issues:** [github.com/naybinho/naybinho-nas/issues](https://github.com/naybinho/naybinho-nas/issues)
- **Documentação:** [docs.naybinho-nas.io](https://docs.naybinho-nas.io)
- **Comunidade:** [discord.gg/naybinho-nas](https://discord.gg/naybinho-nas)
