# 🏗️ Arquitetura do NayBinho NAS

> Documento técnico completo descrevendo os componentes, stack tecnológica, fluxo de dados e decisões de design do NayBinho NAS.

---

## 📐 Visão Geral

O NayBinho NAS é estruturado em camadas bem definidas que separam responsabilidades e permitem escalabilidade e manutenibilidade:

```
┌─────────────────────────────────────────────────────────────────┐
│                    CAMADA DE APRESENTAÇÃO                       │
│              Dashboard Web (React + Tailwind CSS)               │
│         Acesso via navegador · Responsivo · PWA-ready           │
├─────────────────────────────────────────────────────────────────┤
│                    CAMADA DE API / GATEWAY                      │
│           API REST (FastAPI/Python) + WebSocket                 │
│      Autenticação JWT · Rate limiting · Validação               │
├──────────────────────────┬──────────────────────────────────────┤
│    CAMADA DE SERVIÇOS    │       CAMADA DE ORQUESTRAÇÃO         │
│  ┌─────────────────────┐ │  ┌──────────────────────────────────┐│
│  │ Storage Manager     │ │  │ Docker Engine (daemon)           ││
│  │ RAID Controller     │ │  │ App Store Manager                ││
│  │ Network Manager     │ │  │ Container Registry               ││
│  │ User Manager        │ │  │ Volume Manager                   ││
│  │ Notification Svc    │ │  └──────────────────────────────────┘│
│  └─────────────────────┘ │                                      │
├──────────────────────────┴──────────────────────────────────────┤
│                   CAMADA DO SISTEMA OPERACIONAL                 │
│               Ubuntu 26.04.1 LTS (kernel 6.11+)                │
│    systemd · udev · netplan · apparmor · auditd                 │
├─────────────────────────────────────────────────────────────────┤
│                     CAMADA DE HARDWARE                          │
│        CPU x86_64 · RAM · Discos (HDD/SSD/NVMe) · NIC          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🧩 Componentes Principais

### 1. Frontend — Dashboard Web

| Atributo | Valor |
|---|---|
| Framework | React 18 + TypeScript |
| Estilização | Tailwind CSS 3 + shadcn/ui |
| Gráficos | Recharts / Chart.js |
| Estado | Zustand |
| Comunicação | Axios (REST) + native WebSocket |
| Build | Vite |
| PWA | Vite PWA Plugin |

**Páginas principais:**
- `/dashboard` — Visão geral do sistema (CPU, RAM, rede, discos)
- `/storage` — Gerenciamento de discos, volumes e RAID
- `/apps` — Loja de aplicativos Docker
- `/network` — Configuração de rede, DNS, DHCP, VPN
- `/users` — Gerenciamento de usuários e permissões
- `/settings` — Configurações gerais do sistema
- `/logs` — Logs centralizados em tempo real
- `/backups` — Gerenciamento de backups e snapshots

---

### 2. Backend — API Gateway

| Atributo | Valor |
|---|---|
| Runtime | Python 3.12 |
| Framework | FastAPI 0.111+ |
| ASGI Server | Uvicorn |
| Auth | JWT (PyJWT) + bcrypt |
| WebSocket | FastAPI WebSocket |
| Task Queue | Celery + Redis |
| ORM | SQLAlchemy (SQLite para config, PostgreSQL opcional) |
| Docs | OpenAPI automático em `/api/docs` |

**Módulos da API:**
```
/api/v1/
├── /auth          — Login, logout, refresh token, 2FA
├── /system        — Info do sistema, reboot, shutdown
├── /storage       — Discos, partições, montagens, SMART
├── /raid          — Criação, monitoramento e reparo de arrays RAID
├── /docker        — Containers, imagens, volumes, networks
├── /apps          — Loja de apps: listar, instalar, remover, atualizar
├── /network       — Interfaces, DNS, DHCP, firewall, VPN
├── /users         — CRUD de usuários, grupos, cotas
├── /shares        — Samba, NFS, FTP
├── /backups       — Jobs, snapshots, restauração
├── /notifications — Email, Telegram, Discord
└── /logs          — Logs do sistema em streaming
```

---

### 3. Subsistema de Storage

```
Discos Físicos (HDD / SSD / NVMe)
        │
        ▼
   ┌─────────┐    ┌─────────┐    ┌─────────┐
   │  mdadm  │    │   ZFS   │    │  btrfs  │
   │ (RAID   │    │ (zpool) │    │ (single │
   │ linear) │    │         │    │  disk)  │
   └────┬────┘    └────┬────┘    └────┬────┘
        └──────────────┼──────────────┘
                       │
                       ▼
              Volumes / Partições
                       │
              ┌────────┴────────┐
              │                 │
         ┌────▼────┐      ┌─────▼─────┐
         │  Samba  │      │    NFS    │
         │  (SMB)  │      │ (NFS v4)  │
         └─────────┘      └───────────┘
```

**Níveis de RAID suportados:**

| RAID | Discos Mín. | Tolerância a Falhas | Uso Ideal |
|------|-------------|---------------------|-----------|
| 0 | 2 | 0 discos | Máximo desempenho |
| 1 | 2 | 1 disco | Espelhamento simples |
| 5 | 3 | 1 disco | Equilíbrio performance/proteção |
| 6 | 4 | 2 discos | Alta proteção |
| 10 | 4 | 1 por espelho | Melhor performance + proteção |
| Z1 (ZFS) | 3 | 1 disco | RAID-Z1, equivalente ao RAID 5 |
| Z2 (ZFS) | 4 | 2 discos | RAID-Z2, equivalente ao RAID 6 |
| Z3 (ZFS) | 5 | 3 discos | Máxima proteção ZFS |

---

### 4. Sistema de Apps (App Store)

```
App Store UI
     │
     ▼
App Catalog Service ──► catalog.json (definições de apps)
     │
     ▼
App Installer
     │
     ├──► Docker Compose (pull + up)
     ├──► Configuração de volumes NayBinho
     ├──► Configuração de rede (reverse proxy)
     └──► Registro em banco de apps instalados
     
Reverse Proxy (Caddy / Nginx)
     │
     ├──► :8080 → NayBinho Dashboard
     ├──► :8096 → Jellyfin (exemplo)
     ├──► :8181 → Nextcloud (exemplo)
     └──► :9000 → Portainer (exemplo)
```

**Apps disponíveis na loja (exemplos):**

| Categoria | Apps |
|---|---|
| Media | Jellyfin, Plex, Emby, Navidrome, Immich |
| Cloud Pessoal | Nextcloud, Seafile, Syncthing |
| Download | qBittorrent, Transmission, SABnzbd, Sonarr, Radarr |
| Monitoramento | Grafana, Prometheus, Netdata, Uptime Kuma |
| DNS / Rede | Pi-hole, AdGuard Home, Unbound, WireGuard |
| Containers | Portainer, Dozzle, Watchtower |
| Outros | Home Assistant, Vaultwarden, Gitea, Mealie |

---

### 5. Subsistema de Rede

```
Interface Física (eth0 / enp3s0)
        │
        ▼
    Netplan (configuração)
        │
   ┌────┴─────┐
   │          │
Static IP   DHCP Client
        │
        ▼
  Firewall (nftables / ufw)
        │
   ┌────┴───────────────┐
   │                    │
Caddy (Reverse Proxy)  WireGuard VPN
   │
   ├── Dashboard :8080
   ├── API :8081
   └── Apps (portas dinâmicas)
```

---

### 6. Segurança

```
┌────────────────────────────────────────────────┐
│                CAMADAS DE SEGURANÇA             │
│                                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │ Fail2ban │  │ AppArmor │  │  nftables    │ │
│  │ (brute   │  │ (MAC)    │  │  (firewall)  │ │
│  │  force)  │  │          │  │              │ │
│  └──────────┘  └──────────┘  └──────────────┘ │
│                                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐ │
│  │  JWT +   │  │  2FA     │  │  SSL/TLS     │ │
│  │  bcrypt  │  │ (TOTP)   │  │  (Let's      │ │
│  │          │  │          │  │  Encrypt)    │ │
│  └──────────┘  └──────────┘  └──────────────┘ │
│                                                │
│  ┌──────────┐  ┌──────────┐                   │
│  │  auditd  │  │  RBAC    │                   │
│  │  (audit  │  │  (roles) │                   │
│  │  trail)  │  │          │                   │
│  └──────────┘  └──────────┘                   │
└────────────────────────────────────────────────┘
```

---

### 7. Monitoramento e Métricas

```
Coletores:
  ├── node_exporter     → CPU, RAM, disco, rede
  ├── smartmontools     → Saúde dos discos (SMART)
  ├── mdadm --detail    → Status RAID
  ├── zpool status      → Status ZFS
  └── docker stats      → Métricas de containers

Armazenamento:
  └── InfluxDB (time-series) ou Prometheus

Visualização:
  └── Dashboard NayBinho (gráficos integrados)
      └── Grafana (opcional, via App Store)

Alertas:
  └── Alert Manager → Email / Telegram / Discord
```

---

## 📊 Fluxo de Dados — Requisição de API

```
Navegador / Cliente
      │  HTTPS request
      ▼
Caddy (Reverse Proxy + TLS)
      │  Repassa para backend
      ▼
FastAPI (Uvicorn ASGI)
      │
      ├── Middleware: Auth (JWT validation)
      ├── Middleware: Rate Limiting
      ├── Middleware: CORS
      │
      ▼
   Router → Controller
      │
      ├── [Leitura] ──► Banco SQLite / Cache Redis ──► Response JSON
      │
      └── [Escrita] ──► Celery Task Queue
                              │
                         Worker Celery
                              │
                    ┌─────────┴──────────┐
                    │                    │
              Syscall / CLI         Docker API
              (mdadm, zfs,         (criar/parar
               samba, etc.)         container)
                    │                    │
                    └─────────┬──────────┘
                              │
                         WebSocket push → Frontend atualiza UI
```

---

## 🗄️ Modelo de Dados (Simplificado)

```sql
-- Usuários do sistema
users (id, username, email, password_hash, role, 2fa_secret, created_at)

-- Discos físicos detectados
disks (id, device, model, serial, size_gb, health, temperature, last_seen)

-- Arrays RAID
raid_arrays (id, name, level, devices, status, size_gb, created_at)

-- Volumes montados
volumes (id, source_device, mount_point, filesystem, size_gb, used_gb, label)

-- Compartilhamentos
shares (id, name, path, protocol, permissions, users_allowed)

-- Apps instalados
apps (id, name, version, status, docker_compose_path, install_date, ports)

-- Jobs de backup
backup_jobs (id, name, source, destination, schedule_cron, last_run, status)

-- Log de eventos
audit_log (id, user_id, action, resource, details, ip_address, timestamp)
```

---

## 🔄 Boot Sequence

```
BIOS/UEFI
    │
    ▼
GRUB 2 (NayBinho theme)
    │
    ▼
Linux Kernel 6.11+ (Ubuntu 26.04.1)
    │
    ▼
systemd (PID 1)
    │
    ├── network-online.target
    │       └── netplan apply
    │
    ├── naybinho-storage.service
    │       ├── mdadm --assemble --scan
    │       ├── zpool import -a
    │       └── mount -a
    │
    ├── docker.service
    │
    ├── redis.service
    │
    ├── naybinho-backend.service
    │       └── uvicorn naybinho.main:app --host 0.0.0.0 --port 8081
    │
    ├── naybinho-frontend.service (nginx serving React build)
    │
    └── caddy.service (reverse proxy)
    
Sistema pronto — Dashboard acessível em http://<IP>:8080
```

---

## ⚙️ Decisões de Design

| Decisão | Escolha | Justificativa |
|---|---|---|
| OS base | Ubuntu 26.04.1 LTS | Suporte longo, ampla compatibilidade de hardware, grande ecossistema |
| Backend | Python + FastAPI | Excelente para I/O bound, tipagem, OpenAPI automático |
| Frontend | React + Tailwind | Ecossistema maduro, excelente UX, componentes prontos |
| RAID software | mdadm + ZFS | mdadm para RAID linear; ZFS para features avançadas (snapshots, checksums) |
| Reverse proxy | Caddy | TLS automático, configuração simples, HTTP/2 e HTTP/3 |
| Containerização | Docker | Padrão de mercado, amplíssimo catálogo de apps |
| Banco de config | SQLite | Sem overhead de servidor, suficiente para configurações locais |
| Cache / Queue | Redis | Leve, rápido, suporte a pub/sub para WebSocket |

---

## 🗂️ Ver também

- [README.md](../README.md) — Introdução e instalação rápida
- [docs/FEATURES.md](docs/FEATURES.md) — Lista completa de funcionalidades
- [docs/ROADMAP.md](docs/ROADMAP.md) — Plano de desenvolvimento
- [build/build-iso.sh](build/build-iso.sh) — Script de geração da ISO
