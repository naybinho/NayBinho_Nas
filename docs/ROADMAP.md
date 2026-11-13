# 🗺️ Roadmap — NayBinho NAS

> Plano de desenvolvimento do NayBinho NAS, do alpha inicial até a versão estável 1.0.

---

## 📋 Visão Geral das Versões

```
v0.1.0-alpha ──► v0.2.0-alpha ──► v0.3.0-alpha ──► v0.4.0-alpha
     │
     └──► v0.5.0-beta ──► v0.6.0-beta ──► v0.8.0-rc ──► v1.0.0 stable
```

---

## 🔨 v0.1.0-alpha — Fundação
> **Status:** 🔨 Em desenvolvimento  
> **Previsão:** Q1 2026

### Objetivos
Estabelecer a fundação do sistema: ISO bootável, instalador, dashboard básico e gerenciamento essencial de storage.

### Entregas

#### 🏗️ Build & Instalação
- [x] Estrutura de projeto definida
- [x] Script de build da ISO (`build-iso.sh`)
- [x] Preseed para instalação automatizada
- [x] GRUB customizado com tema NayBinho
- [ ] ISO bootável gerada e testada
- [ ] Instalador em modo texto com wizard
- [ ] Suporte a UEFI e BIOS legado

#### 🖥️ Dashboard Web (MVP)
- [ ] Projeto React iniciado com Tailwind CSS
- [ ] Layout base: sidebar, header, main content
- [ ] Página de login com JWT
- [ ] Dashboard home: CPU, RAM, disco, rede (tempo real via WebSocket)
- [ ] Tema dark/light

#### 🔧 Backend (MVP)
- [ ] FastAPI configurado com autenticação JWT
- [ ] Endpoints: `/api/v1/system` (info, reboot, shutdown)
- [ ] Endpoints: `/api/v1/storage` (listar discos, montar volumes)
- [ ] WebSocket para push de métricas
- [ ] Integração com `node_exporter`

#### 💾 Storage (básico)
- [ ] Listagem de discos via `lsblk`
- [ ] Informações SMART via `smartmontools`
- [ ] Montagem/desmontagem de volumes
- [ ] Exibição de uso de disco

---

## 📦 v0.2.0-alpha — Storage & RAID
> **Status:** 📋 Planejado  
> **Previsão:** Q2 2026

### Objetivos
Implementar o gerenciamento completo de RAID e compartilhamentos de arquivos.

### Entregas

#### 💾 RAID Manager
- [ ] Interface para criação de arrays RAID 0, 1, 5, 6, 10
- [ ] Monitoramento de status do array em tempo real
- [ ] Alertas de falha de disco
- [ ] Reconstrução automática de array
- [ ] Substituição a quente (hot-spare)

#### 🗄️ ZFS
- [ ] Criação de zpools via interface
- [ ] Snapshots manuais e agendados
- [ ] Send/receive para backup entre pools
- [ ] Compressão e deduplicação configuráveis

#### 📁 Compartilhamentos
- [ ] Configuração de shares Samba (SMB/CIFS)
- [ ] Configuração de exports NFS v4
- [ ] Gerenciamento de usuários e permissões por share
- [ ] Cotas de disco por usuário/grupo

#### 📊 Storage Dashboard
- [ ] Visualização gráfica do RAID (discos, status, uso)
- [ ] Mapa de calor de uso por diretório
- [ ] Histórico de IOPS e throughput

---

## 🐳 v0.3.0-alpha — Docker & App Store
> **Status:** 📋 Planejado  
> **Previsão:** Q3 2026

### Objetivos
Integrar Docker nativo e lançar a loja de aplicativos.

### Entregas

#### 🐳 Docker Manager
- [ ] Listagem de containers com status
- [ ] Start/stop/restart/remove de containers
- [ ] Logs de container em tempo real
- [ ] Gerenciamento de imagens (pull, remove)
- [ ] Gerenciamento de volumes Docker
- [ ] Gerenciamento de redes Docker

#### 🏪 App Store
- [ ] Catálogo de apps com 30+ aplicativos curados
- [ ] Instalação com 1 clique via Docker Compose
- [ ] Configuração guiada por app (portas, volumes, vars de ambiente)
- [ ] Atualização de apps instalados
- [ ] Remoção com limpeza de dados opcional

**Apps no lançamento:**
- Media: Jellyfin, Immich, Navidrome
- Cloud: Nextcloud, Syncthing
- Downloads: qBittorrent, Sonarr, Radarr
- DNS: Pi-hole, AdGuard Home
- Monitoramento: Netdata, Uptime Kuma
- Utils: Portainer, Vaultwarden, Gitea

#### 🌐 Reverse Proxy
- [ ] Caddy integrado para roteamento de apps
- [ ] SSL automático com Let's Encrypt
- [ ] Subdomínios automáticos por app

---

## 🔐 v0.4.0-alpha — Rede & Segurança
> **Status:** 📋 Planejado  
> **Previsão:** Q4 2026

### Objetivos
Adicionar configuração de rede avançada e camadas de segurança robustas.

### Entregas

#### 🌐 Rede
- [ ] Configuração de IP estático / DHCP via interface
- [ ] Suporte a múltiplas interfaces de rede
- [ ] Bonding/LACP para link aggregation
- [ ] VLAN tagging
- [ ] Servidor DHCP integrado (opcional)
- [ ] WireGuard VPN (servidor e cliente)

#### 🔐 Segurança
- [ ] Autenticação 2FA (TOTP via app autenticador)
- [ ] Fail2ban configurado para SSH e dashboard
- [ ] Firewall (nftables) com regras via interface
- [ ] Relatório de auditoria (quem fez o quê e quando)
- [ ] Scanner de vulnerabilidades básico
- [ ] SSH hardening automático

#### 👥 Usuários & Permissões
- [ ] Sistema de roles: Admin, Operador, Usuário
- [ ] SSO opcional (LDAP/Active Directory)
- [ ] API keys para integração

---

## 🔄 v0.5.0-beta — Backups & Notificações
> **Status:** 📋 Planejado  
> **Previsão:** Q1 2027

### Objetivos
Implementar sistema de backups robusto e notificações inteligentes.

### Entregas

#### 💾 Backup Manager
- [ ] Jobs de backup agendados (cron visual)
- [ ] Backup para destino local (disco externo)
- [ ] Backup para nuvem: S3, Backblaze B2, Google Drive, OneDrive
- [ ] Backup incremental com deduplicação (restic)
- [ ] Restauração parcial (arquivo/pasta) ou total
- [ ] Verificação de integridade automática
- [ ] Retenção configurável (N últimas versões)

#### 🔔 Notificações
- [ ] Email (SMTP configurável)
- [ ] Telegram bot
- [ ] Discord webhook
- [ ] Pushover / Gotify
- [ ] Alertas configuráveis: disco cheio, RAID degradado, temperatura, falha de backup
- [ ] Relatório semanal de saúde do sistema

---

## 📊 v0.6.0-beta — Monitoramento Avançado
> **Status:** 📋 Planejado  
> **Previsão:** Q2 2027

### Objetivos
Monitoramento completo com histórico, alertas e integração com Grafana.

### Entregas

- [ ] Integração com Prometheus + InfluxDB
- [ ] Grafana via App Store com dashboards pré-configurados
- [ ] Histórico de 90 dias de métricas
- [ ] Alertas baseados em thresholds configuráveis
- [ ] Relatórios PDF agendados
- [ ] Dashboard de saúde de discos com previsão de falha (ML básico)
- [ ] Monitoramento de temperatura com controle de fan (se suportado)

---

## 🚀 v0.8.0-rc — Release Candidate
> **Status:** 📋 Planejado  
> **Previsão:** Q3 2027

### Objetivos
Estabilização, polimento e preparação para release estável.

### Entregas

- [ ] Testes end-to-end automatizados
- [ ] Documentação completa do usuário
- [ ] Wizard de configuração inicial (first-run)
- [ ] Sistema de atualização OTA (over-the-air)
- [ ] Importação de configuração de TrueNAS/OMV
- [ ] CLI tool (`naybinho-cli`)
- [ ] Suporte a ZFS encryption nativa
- [ ] Auditoria de segurança externa

---

## ✅ v1.0.0 — Stable Release
> **Status:** 📋 Planejado  
> **Previsão:** Q4 2027

### Objetivos
Release estável, completa e suportada a longo prazo.

### Entregas

- [ ] Todos os recursos das versões anteriores estabilizados
- [ ] ISO testada em 10+ configurações de hardware diferentes
- [ ] Suporte a ARM64 (Raspberry Pi 5, outros SBCs)
- [ ] App Store com 100+ aplicativos
- [ ] Sistema de plugins da comunidade
- [ ] Certificação de hardware parceiros
- [ ] LTS com suporte garantido até 2030

---

## 🗓️ Timeline Visual

```
2026 Q1  │████░░░░│ v0.1.0-alpha (Fundação)
2026 Q2  │░░░░████│ v0.2.0-alpha (Storage & RAID)
2026 Q3  │████░░░░│ v0.3.0-alpha (Docker & Apps)
2026 Q4  │░░░░████│ v0.4.0-alpha (Rede & Segurança)
2027 Q1  │████░░░░│ v0.5.0-beta  (Backups)
2027 Q2  │░░░░████│ v0.6.0-beta  (Monitoramento)
2027 Q3  │████░░░░│ v0.8.0-rc    (Release Candidate)
2027 Q4  │░░░░████│ v1.0.0       (Stable 🎉)
```

---

## 🤝 Como Contribuir para o Roadmap

Tem uma sugestão? Abra uma [issue](https://github.com/naybinho/naybinho-nas/issues) com a tag `roadmap` ou vote nas issues existentes com 👍.

Funcionalidades mais votadas pela comunidade têm prioridade nas próximas versões!
