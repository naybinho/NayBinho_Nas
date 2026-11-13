<div align="center">

<img src="docs/assets/logo.png" alt="NayBinho NAS Logo" width="200"/>

# 🏠 NayBinho NAS

**Sistema Operacional para Home Lab & NAS — Gratuito, Moderno e Poderoso**

[![Version](https://img.shields.io/badge/version-0.1.0--alpha-blue?style=for-the-badge)](https://github.com/naybinho/naybinho-nas/releases)
[![Base](https://img.shields.io/badge/base-Ubuntu%2026.04.1%20LTS-orange?style=for-the-badge&logo=ubuntu)](https://ubuntu.com)
[![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Native-2496ED?style=for-the-badge&logo=docker)](https://docker.com)
[![RAID](https://img.shields.io/badge/RAID-0--10-purple?style=for-the-badge)](docs/FEATURES.md)
[![ZFS](https://img.shields.io/badge/ZFS-Supported-red?style=for-the-badge)](docs/FEATURES.md)
[![Build ISO](https://img.shields.io/badge/build-passing-brightgreen?style=for-the-badge)]()
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen?style=for-the-badge)](CONTRIBUTING.md)

> Um sistema operacional completo para servidores home lab e NAS, baseado em Ubuntu 26.04.1 LTS,  
> com dashboard web moderno, Docker nativo, loja de apps, suporte a RAID 0–10 e muito mais.

</div>

---

## 📸 Screenshots

<div align="center">

| Dashboard Principal | Gerenciador de Storage | Loja de Apps |
|:---:|:---:|:---:|
| ![Dashboard](docs/assets/screenshots/dashboard.png) | ![Storage](docs/assets/screenshots/storage.png) | ![AppStore](docs/assets/screenshots/appstore.png) |

| Monitor de Sistema | RAID Manager | Configurações |
|:---:|:---:|:---:|
| ![Monitor](docs/assets/screenshots/monitor.png) | ![RAID](docs/assets/screenshots/raid.png) | ![Settings](docs/assets/screenshots/settings.png) |

> ⚠️ _Screenshots são mockups — produto em desenvolvimento._

</div>

---

## ✨ Funcionalidades Principais

- 🖥️ **Dashboard Web Moderno** — Interface responsiva em React, acessível por navegador em qualquer dispositivo da rede
- 🐳 **Docker Nativo** — Gerenciamento de containers com interface gráfica integrada
- 🏪 **Loja de Apps** — Instale Jellyfin, Nextcloud, Plex, Portainer, Pi-hole e muito mais com 1 clique
- 💾 **RAID Avançado** — Suporte a RAID 0, 1, 5, 6, 10 via mdadm e ZFS
- 📁 **Compartilhamento de Arquivos** — Samba (SMB/CIFS) e NFS prontos para uso
- 🔐 **Segurança** — Fail2ban, firewall integrado, autenticação 2FA, SSL automático
- 📊 **Monitoramento** — CPU, RAM, disco, rede em tempo real com histórico
- 🔄 **Backups Automáticos** — Snapshots ZFS e backup incremental para nuvem
- 🌐 **DNS & DHCP** — Servidor DNS local e DHCP gerenciável via interface
- 🔔 **Notificações** — Email, Telegram, Discord para alertas de sistema
- ⚡ **Leve e Eficiente** — Mínimo de 2GB RAM, funciona em hardware de 2010+
- 🆓 **100% Gratuito** — Open source, sem licenças pagas, sem telemetria

---

## 🚀 Instalação Rápida

### Requisitos Mínimos

| Componente | Mínimo | Recomendado |
|---|---|---|
| CPU | x86_64 dual-core | x86_64 quad-core |
| RAM | 2 GB | 8 GB+ |
| Disco do Sistema | 16 GB | 32 GB SSD |
| Discos de Dados | 1× qualquer tamanho | 2×+ para RAID |
| Rede | 100 Mbps | 1 Gbps |

### Opção 1 — ISO (Recomendado)

```bash
# 1. Baixe a ISO mais recente
wget https://github.com/naybinho/naybinho-nas/releases/latest/download/naybinho-nas-1.0.0-amd64.iso

# 2. Grave em um pendrive (substitua /dev/sdX pelo seu dispositivo)
sudo dd if=naybinho-nas-1.0.0-amd64.iso of=/dev/sdX bs=4M status=progress sync

# 3. Inicialize o servidor pelo pendrive e siga o instalador
```

### Opção 2 — Instalar sobre Ubuntu existente

```bash
# Execute como root em um Ubuntu 26.04 limpo
curl -fsSL https://get.naybinho.io/install.sh | sudo bash
```

### Opção 3 — Build da ISO manualmente

```bash
git clone https://github.com/naybinho/naybinho-nas.git
cd naybinho-nas/build
sudo bash build-iso.sh
# ISO gerada em: build/output/naybinho-nas-1.0.0-amd64.iso
```

---

## 🔧 Pós-Instalação

Após a instalação, acesse o painel web:

```
http://<IP-do-servidor>:8080
```

Login padrão:
- **Usuário:** `admin`  
- **Senha:** Definida durante a instalação

---

## 📂 Estrutura do Projeto

```
naybinho-nas/
├── build/                  # Scripts de build da ISO
│   ├── build-iso.sh        # Script principal de geração da ISO
│   ├── packages.list       # Pacotes incluídos na ISO
│   ├── preseed.cfg         # Instalação automatizada
│   └── grub.cfg            # Bootloader customizado
├── src/
│   ├── backend/            # API REST (Node.js / Python FastAPI)
│   ├── frontend/           # Dashboard web (React + Tailwind)
│   ├── services/           # Serviços do sistema (systemd units)
│   └── scripts/            # Scripts de configuração e manutenção
├── apps/                   # Definições de apps da loja (Docker Compose)
├── docs/                   # Documentação completa
│   ├── ROADMAP.md
│   ├── FEATURES.md
│   └── assets/
├── README.md
└── ARCHITECTURE.md
```

---

## 🗺️ Roadmap Rápido

| Versão | Status | Destaque |
|---|---|---|
| v0.1.0-alpha | 🔨 Em desenvolvimento | Estrutura base, ISO bootável, dashboard básico |
| v0.2.0-alpha | 📋 Planejado | Loja de apps, RAID manager |
| v0.5.0-beta | 📋 Planejado | ZFS, backups, notificações |
| v1.0.0 | 📋 Planejado | Release estável completa |

Ver [ROADMAP completo](docs/ROADMAP.md).

---

## 🤝 Contribuindo

Contribuições são bem-vindas! Veja [CONTRIBUTING.md](CONTRIBUTING.md) para começar.

```bash
git clone https://github.com/naybinho/naybinho-nas.git
cd naybinho-nas
# Faça suas alterações e abra um Pull Request
```

---

## 📄 Licença

Este projeto está licenciado sob a [MIT License](LICENSE).

---

<div align="center">

Feito com ❤️ para a comunidade home lab brasileira e mundial.

**[Website](https://naybinho.io)** · **[Documentação](docs/)** · **[Issues](https://github.com/naybinho/naybinho-nas/issues)** · **[Discord](https://discord.gg/naybinho)**

</div>
