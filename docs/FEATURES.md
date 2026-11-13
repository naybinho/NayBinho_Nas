# ✨ Funcionalidades — NayBinho NAS

> Lista completa e detalhada de todas as funcionalidades do NayBinho NAS.

---

## 🖥️ Dashboard Web

### Interface Geral
- **Design moderno**: Interface limpa, responsiva, com tema dark e light
- **Acesso por navegador**: Sem necessidade de instalar nada no cliente — funciona em qualquer dispositivo
- **PWA (Progressive Web App)**: Pode ser instalado na tela inicial do celular/tablet
- **Multilíngue**: Português (PT-BR), Inglês, Espanhol (planejado)
- **Acessibilidade**: Compatível com leitores de tela, alto contraste

### Dashboard Home
- Resumo em tempo real: CPU, RAM, swap, temperatura do processador
- Uso de disco por volume com gráficos de barra
- Tráfego de rede (upload/download) em tempo real
- Status dos arrays RAID (saudável, degradado, reconstruindo)
- Containers Docker em execução
- Eventos recentes do sistema
- Uptime do servidor
- Alertas pendentes

---

## 💾 Gerenciamento de Storage

### Discos Físicos
- Detecção automática de todos os discos (HDD, SSD, NVMe, USB)
- Informações detalhadas: modelo, fabricante, número serial, tamanho, RPM
- **SMART Monitoring**: temperatura, horas de uso, setores remapeados, contagem de erros
- Indicador visual de saúde: 🟢 Saudável / 🟡 Atenção / 🔴 Crítico
- Previsão de falha baseada em dados SMART
- Teste SMART agendável (curto e longo)
- Secure Erase (apagamento seguro) via interface

### Partições e Volumes
- Criar, editar e remover partições via interface
- Suporte a filesystems: ext4, xfs, btrfs, ZFS, NTFS (leitura), exFAT
- Montagem e desmontagem com confirmação
- Rótulos personalizados para volumes
- Cotas por volume (quota)
- Histórico de operações de disco

### RAID Manager
| Nível | Descrição | Discos Mín. | Tolerância |
|-------|-----------|-------------|------------|
| RAID 0 | Striping — máxima velocidade, sem redundância | 2 | 0 |
| RAID 1 | Mirroring — redundância simples | 2 | 1 |
| RAID 5 | Paridade distribuída — equilíbrio | 3 | 1 |
| RAID 6 | Dupla paridade — alta proteção | 4 | 2 |
| RAID 10 | Stripe de mirrors — velocidade + proteção | 4 | 1/espelho |

**Funcionalidades do RAID Manager:**
- Wizard de criação passo a passo
- Visualização gráfica do array com status de cada disco
- Monitoramento de reconstrução com estimativa de tempo
- Hot-spare (disco reserva automático)
- Substituição de disco guiada (passo a passo)
- Relatório de saúde do array
- Alertas de degradação via email/Telegram

### ZFS
- Criação de zpools (single, mirror, RAID-Z1/Z2/Z3)
- Datasets e zvols
- **Snapshots**: manuais, agendados por cron, listagem e restauração
- Compressão: lz4, zstd, gzip (configurável por dataset)
- Deduplicação de dados
- Checksums automáticos (integridade de dados)
- Scrub agendável (verificação de integridade)
- Send/receive para backup entre servidores
- ARC (cache) e L2ARC (SSD cache) configurável

---

## 📁 Compartilhamento de Arquivos

### Samba (SMB/CIFS)
- Criação e gerenciamento de shares via interface
- Controle de acesso por usuário e grupo
- Suporte a ACLs do Windows
- Senhas independentes do sistema (smbpasswd)
- Visível no "Explorador de Rede" do Windows automaticamente
- Suporte a Time Machine (backup do macOS via Samba)
- Auditoria de acesso a arquivos

### NFS
- Exports NFS v3 e v4
- Controle por IP/subnet
- Opções: read-only, squash de root, kerberos (opcional)
- Performance otimizada com rsize/wsize automático

### FTP/SFTP
- Servidor FTP com TLS (FTPS)
- SFTP via OpenSSH
- Usuários FTP isolados (chroot)
- Limite de largura de banda por usuário

### WebDAV
- Acesso a arquivos via HTTP/HTTPS
- Compatível com clientes WebDAV (Rclone, Windows, macOS)

---

## 🐳 Docker & Containers

### Docker Manager
- Listagem de todos os containers com status em tempo real
- Start, stop, restart, pause, remove de containers
- Logs de container ao vivo com busca
- Terminal integrado no container (exec -it)
- Uso de CPU, RAM, rede e disco por container
- Variáveis de ambiente (visualização segura)
- Port mappings e volumes mapeados

### Gerenciamento de Imagens
- Busca no Docker Hub diretamente da interface
- Pull, tag e remove de imagens
- Histórico de layers da imagem
- Vulnerabilidades (integração com Trivy, opcional)

### Redes e Volumes Docker
- Criar e remover redes (bridge, host, overlay)
- Inspecionar e conectar containers a redes
- Criar, montar e fazer backup de volumes Docker

---

## 🏪 Loja de Aplicativos & Multi-Repositórios

### Suporte a Múltiplas Lojas & Fontes Externas
- **Lojas Nativas e Comunitárias Integradas:**
  - **NayBinho Oficial**: Catálogo otimizado com mais de 100 aplicações de Home Lab.
  - **CasaOS Play Store**: `https://play.cuse.eu.org/store.json`
  - **BigBear CasaOS Store**: `https://cdn.jsdelivr.net/gh/bigbeartechworld/big-bear-casaos@gh-pages/store.json`
  - **Zima AppStore**: `https://chicohaager.github.io/zima-appstore/store.json`
- **Adição Dinâmica de Lojas:**
  - Opção na interface web e API para cadastrar qualquer URL de `store.json` externa.
  - Sincronização automática em segundo plano com caching local resiliente.
  - Ativação e desativação seletiva de repositórios.
  - Filtro por loja no catálogo de aplicações.

### Categorias e Apps Homologados

**🎬 Media & Entretenimento**
- Jellyfin — Servidor de mídia open source
- Plex — Servidor de mídia premium
- Emby — Servidor de mídia
- Navidrome — Servidor de música
- Immich — Backup de fotos (alternativa ao Google Fotos)
- Photoprism — Galeria de fotos com IA

**☁️ Cloud Pessoal**
- Nextcloud — Suite completa de produtividade pessoal
- Seafile — Sincronização de arquivos rápida
- Syncthing — Sincronização P2P
- Vaultwarden — Gerenciador de senhas (compatível Bitwarden)

**⬇️ Downloads**
- qBittorrent — Cliente torrent com interface web
- Transmission — Cliente torrent leve
- SABnzbd — Newsgroup downloader
- NZBGet — Newsgroup downloader alternativo
- Sonarr — Automação de séries
- Radarr — Automação de filmes
- Lidarr — Automação de música
- Readarr — Automação de livros
- Prowlarr — Indexer manager

**🌐 Rede & DNS**
- Pi-hole — Bloqueio de anúncios para toda a rede
- AdGuard Home — DNS com bloqueio de anúncios
- Unbound — Resolver DNS recursivo
- WireGuard Easy — VPN WireGuard com interface

**📊 Monitoramento**
- Netdata — Monitoramento em tempo real
- Grafana — Dashboards e gráficos
- Prometheus — Coleta de métricas
- Uptime Kuma — Monitor de uptime
- Dozzle — Logs de containers ao vivo

**🛠️ Utilitários**
- Portainer — Gerenciamento de Docker
- Watchtower — Atualização automática de containers
- Duplicati — Backup para nuvem
- File Browser — Gerenciador de arquivos web
- Code Server — VS Code no navegador

**🏠 Smart Home**
- Home Assistant — Automação residencial
- Node-RED — Fluxos de automação visual
- Mosquitto — Broker MQTT

**🔧 Dev & Infra**
- Gitea — Git server self-hosted
- Drone CI — CI/CD self-hosted
- Mealie — Gerenciador de receitas

---

## 🌐 Configuração de Rede

- **IP estático ou DHCP** por interface via interface web
- **Hostname e domínio** configuráveis
- **DNS**: servidor DNS primário e secundário configuráveis
- **Bonding/LACP**: agregação de links para maior throughput
- **VLAN**: suporte a 802.1Q
- **Wake-on-LAN**: ligar o servidor remotamente
- **IPv6**: suporte completo
- **Diagnósticos**: ping, traceroute, DNS lookup, nmap básico via interface

---

## 🔐 Segurança

### Autenticação
- Login com usuário e senha
- **Autenticação de dois fatores (2FA)** via TOTP (Google Authenticator, Authy)
- Tokens JWT com expiração configurável
- Sessões ativas com revogação
- Bloqueio após tentativas falhas configurável

### Firewall
- Configuração de regras nftables via interface
- Perfis predefinidos: NAS básico, servidor web, isolado
- Regras por IP, porta, protocolo e interface
- Log de tráfego bloqueado

### Proteção contra Ataques
- Fail2ban integrado: bloqueia IPs após tentativas falhas (SSH, web)
- Rate limiting na API
- Proteção CSRF
- Headers de segurança HTTP (HSTS, CSP, X-Frame-Options)

### Certificados SSL
- Let's Encrypt automático (via Caddy)
- Suporte a certificado customizado (upload)
- Certificado auto-assinado para uso local

### Auditoria
- Log de todas as ações administrativas
- Quem fez o quê e quando (IP, usuário, ação, recurso)
- Exportação de logs de auditoria

---

## 🔔 Notificações e Alertas

### Canais
- **Email** (SMTP configurável — Gmail, Outlook, servidor próprio)
- **Telegram** (bot com token configurável)
- **Discord** (webhook)
- **Pushover** (mobile push)
- **Gotify** (self-hosted push)
- **Slack** (webhook)

### Eventos Notificáveis
- 🔴 Disco com falha ou degradação SMART
- 🔴 Array RAID degradado ou falhou
- 🟡 Disco com temperatura alta (threshold configurável)
- 🟡 Uso de disco acima de X% (threshold configurável)
- 🟡 RAM acima de X% por período prolongado
- 🔴 Falha em job de backup
- ✅ Backup concluído com sucesso
- 🔴 Container parou inesperadamente
- 🟡 Atualização de app disponível
- 🔵 Login bem-sucedido (opcional)
- 🔴 Login com falha repetido / IP bloqueado pelo Fail2ban
- 📊 Relatório semanal de saúde do sistema

---

## 🔄 Backups

- **Destinos**: disco externo, compartilhamento de rede (SMB/NFS), S3, Backblaze B2, Google Drive, OneDrive, SFTP remoto
- **Incremental**: apenas alterações são enviadas (via restic)
- **Deduplicação**: dados duplicados não ocupam espaço extra
- **Criptografia**: backups criptografados no destino (AES-256)
- **Agendamento**: cron visual (diário, semanal, horário, etc.)
- **Retenção**: política de retenção configurável (N últimos backups)
- **Verificação**: checagem automática de integridade dos backups
- **Restauração**: arquivo individual, pasta ou restauração completa
- **Snapshots ZFS**: snapshots locais automáticos e rápidos

---

## 📊 Monitoramento do Sistema

### Métricas em Tempo Real
- CPU (por core, frequência, temperatura)
- RAM e swap (uso, disponível, cache)
- Discos (uso, IOPS, throughput, temperatura)
- Rede (throughput por interface, pacotes, erros)
- Containers (CPU, RAM, rede por container)
- Processos (top 10 por CPU/RAM)

### Histórico
- Gráficos históricos configuráveis (1h, 24h, 7d, 30d, 90d)
- Armazenamento eficiente de time-series

### Logs Centralizados
- Logs do sistema (`/var/log/syslog`, `journalctl`)
- Logs de containers Docker
- Logs do RAID e ZFS
- Busca full-text nos logs
- Filtros por serviço, severidade e período
- Download de logs

---

## ⚡ Performance e Eficiência

- **Consumo mínimo**: ~300MB RAM com todos os serviços base rodando
- **Requisito mínimo**: CPU dual-core x86_64, 2GB RAM, 16GB de disco de sistema
- **Hardware de 2010+**: compatível com hardware antigo (desde que x86_64)
- **SSD opcional**: melhora drasticamente a performance, mas HDD funciona
- **I/O agendável**: operações pesadas (scrub, rebuild) com limite de I/O configurável para não impactar usuários
- **Cache inteligente**: ARC do ZFS, cache de leitura em SSD (L2ARC)

---

## 🔧 Manutenção e Administração

- **Atualização do sistema**: via interface (apt upgrade)
- **Atualização do NayBinho NAS**: atualização OTA one-click
- **Reinicialização e desligamento** via interface com confirmação
- **Agendamento de manutenção**: agendar reinicializações para madrugada
- **CLI tool** (`naybinho-cli`): todas as operações também disponíveis via linha de comando
- **Importação de configuração**: importar de TrueNAS/OMV (planejado)
- **Exportação de configuração**: backup das configurações do NAS

---

## 🆓 Gratuito e Open Source

- 100% gratuito — sem planos pagos, sem licenças
- Código aberto (MIT License)
- Sem telemetria ou envio de dados
- Sem dependência de serviços externos (exceto opcionais como Let's Encrypt)
- Comunidade ativa com suporte via Discord, fórum e GitHub Issues
