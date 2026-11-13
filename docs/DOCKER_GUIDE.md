# Guia Definitivo do Docker & App Store — NayBinho NAS

O **NayBinho NAS** integra o subsistema Docker de maneira nativa e de baixo nível ao sistema operacional **Ubuntu 26.04.1 LTS**. Projetado sob medida para entusiastas de Home Lab, auto-hospedagem (self-hosting) e pequenos escritórios, o sistema une a flexibilidade de contêineres OCI com a confiabilidade do sistema de arquivos ZFS, garantindo persistência atômica, controle de recursos por cgroups v2 e instalação com um clique através da **App Store** integrada.

---

## 1. Visão Geral da Arquitetura de Contêineres

A pilha de contêineres do NayBinho NAS é construída com foco em resiliência, isolamento e baixa latência:

```
+-----------------------------------------------------------------------------------+
|                           Interface Web / REST API                                |
|           (App Store, Gerenciador de Contêineres, Métricas & Logs)                |
+-----------------------------------------------------------------------------------+
       |                                      |                                |
       v                                      v                                v
+------------------+                 +------------------+             +--------------------+
| App Store Engine |                 |  Traefik Proxy   |             |   Docker Daemon    |
| (catalog.json)   |                 | (SSL automático) |             |  (dockerd nativo)  |
+------------------+                 +------------------+             +--------------------+
       |                                      |                                |
       +--------------------------------------+--------------------------------+
                                              |
       +-----------------------------------------------------------------------+
       |                               Camada do SO                            |
       |  - Ubuntu 26.04.1 LTS Kernel 6.8+ (cgroups v2, systemd)               |
       |  - Rede Bridge: naybinho_network (172.28.0.0/16 isolada)              |
       |  - Storage Pool ZFS: /tank/appdata/<app_id> (snapshots automáticos)   |
       +-----------------------------------------------------------------------+
```

### Principais Pilares Arquiteturais
- **Daemon Docker Nativo**: Executado como serviço `systemd` (`dockerd`), com soquete UNIX seguro `/var/run/docker.sock` restrito ao grupo `docker`.
- **Storage Driver Otimizado**: Integração nativa com pools ZFS (`/tank/appdata/`), com compressão ZSTD habilitada, snapshots atômicos pré-atualização e isolamento de datasets.
- **Rede Padrão Unificada (`naybinho_network`)**: Rede bridge dedicada (`172.28.0.0/16`) que fornece resolução interna de DNS por nome de contêiner (`jellyfin`, `postgres`, `nextcloud`), evitando conflito com a LAN física do usuário.
- **Padrão Não-Root PUID/PGID**: Por padrão, todas as aplicações rodam sob o usuário `nasuser` (`PUID=1000`, `PGID=1000`), prevenindo que contêineres corrompam permissões do host.
- **Isolamento de Segurança**: Diretiva `no-new-privileges:true` ativada por padrão para mitigar elevação de privilégios via binários SUID.

---

## 2. A Loja de Aplicações (App Store) & Multi-Repositórios

A App Store do NayBinho NAS possui arquitetura aberta e **multi-repositório**, permitindo integrar tanto a loja oficial quanto lojas comunitárias e repositórios populares de CasaOS e ZimaOS via URLs de `store.json`.

### Lojas Pré-Configuradas de Fábrica:

1. **NayBinho Oficial** (`local`):
   - Mais de 107 aplicações de Home Lab homologadas, otimizadas para Ubuntu 26.04.1 LTS com transcodificação por hardware e volumes persistentes em ZFS/RAID.
2. **BigBear CasaOS (GitHub Master Archive .zip)**:
   - URL: `https://github.com/bigbeartechworld/big-bear-casaos/archive/refs/heads/master.zip`
   - Extrai automaticamente centenas de aplicações e stacks completas do repositório Git master.
3. **CasaOS Play Store**:
   - URL: `https://play.cuse.eu.org/store.json`
   - Centenas de aplicações comunitárias, utilitários, web tools e servidores.
4. **BigBear CasaOS Store (CDN)**:
   - URL: `https://cdn.jsdelivr.net/gh/bigbeartechworld/big-bear-casaos@gh-pages/store.json`
   - Biblioteca mantida pela comunidade BigBearTechWorld via jsDelivr CDN.
5. **Zima AppStore**:
   - URL: `https://chicohaager.github.io/zima-appstore/store.json`
   - Repositório de aplicações curadas para ecossistemas ZimaOS / CasaOS por Chico Haager.

### Adicionando Novas Lojas Personalizadas:
Você pode adicionar qualquer loja compatível através da interface web ou da API:
1. Acesse **App Store** na interface web.
2. Clique no botão **Gerenciar Lojas**.
3. Na seção *Adicionar Nova Loja*, informe o **Nome** e a **URL do `store.json`**.
4. Clique em **Adicionar e Sincronizar Loja**. O sistema baixará o catálogo em segundo plano, normalizará os metadados e disponibilizará todos os aplicativos imediatamente com filtros por loja e categoria.

Via API REST:
```bash
curl -X POST http://<IP_DO_NAS>:8000/api/store/sources \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Minha Loja", "url": "https://meu-servidor/store.json", "type": "casaos"}'
```

### Categorias Disponíveis

| Categoria | ID | Ícone | Descrição | Principais Aplicações |
|---|---|---|---|---|
| **Media & Streaming** | `media` | `film` | Servidores multimídia, streaming e transcodificação | Jellyfin, Plex, Emby, Navidrome, Immich, Calibre-Web, Audiobookshelf |
| **Downloads & Usenet** | `downloads` | `download-cloud` | Clientes P2P, Usenet e indexadores automatizados | qBittorrent, Transmission, Sonarr, Radarr, Lidarr, Prowlarr, SABnzbd |
| **Home Automation & IoT** | `automation` | `cpu` | Hubs domóticos, automação visual e corretores MQTT | Home Assistant, Node-RED, Mosquitto MQTT, Zigbee2MQTT, n8n, ESPHome |
| **Development & CI/CD** | `development` | `code` | Ambientes de código, Git e execução de LLMs | Gitea, Forgejo, Code-Server, Drone CI, Ollama, Open WebUI, IT-Tools |
| **Cloud Storage & Backup** | `storage` | `hard-drive` | Nuvem pessoal, sync contínuo e repositórios de backup | Nextcloud, FileBrowser, Syncthing, Seafile, MinIO S3, Duplicati, Kopia |
| **Network & DNS** | `network` | `globe` | DNS com bloqueio, VPNs mesh e proxies reversos | Pi-hole, AdGuard Home, WireGuard Easy, Tailscale, Nginx Proxy Manager, Traefik |
| **Security & Privacy** | `security` | `shield` | Cofres de credenciais, IPS colaborativo e autenticação | Vaultwarden, Authelia, Authentik, CrowdSec, SearXNG, Whoogle |
| **Monitoring & Metrics** | `monitoring` | `activity` | Telemetria em tempo real, painéis e alertas | Uptime Kuma, Netdata, Grafana, Prometheus, InfluxDB, Portainer CE, Dockge |
| **Productivity & Office** | `productivity` | `briefcase` | Gestão documental, wikis e finanças pessoais | Paperless-ngx, Stirling-PDF, Vikunja, BookStack, Actual Budget, Mealie |
| **Databases & Caches** | `database` | `database` | Motores SQL, NoSQL e bancos de séries temporais | PostgreSQL, MariaDB, Redis Stack, MongoDB Community |

---

## 3. Guia de Instalação e Ciclo de Vida pela Interface Web

### Instalação em 1 Clique (One-Click Deploy)
1. Abra o painel do NayBinho NAS: `http://<IP_DO_NAS>` ou `https://naybinho.local`.
2. Navegue até o menu **App Store** na barra lateral.
3. Pesquise a aplicação pelo nome, funcionalidade ou filtre por categoria.
4. Clique no card do aplicativo para abrir o modal de detalhes técnicos:
   - Descrição e funcionalidades.
   - Requisitos mínimos de CPU, RAM e armazenamento.
   - Portas TCP/UDP que serão expostas no host.
   - Volumes de dados persistentes.
   - Parâmetros de ambiente (`PUID`, `PGID`, `TZ`, chaves de admin).
5. Clique em **Instalar**:
   - O daemon baixa a imagem oficial do registry.
   - O diretório `/tank/appdata/<app_id>/` é provisionado com permissões corretas.
   - O arquivo `docker-compose.yml` local é gerado baseado no template do catálogo.
   - O contêiner é inicializado na rede `naybinho_network`.
6. Ao término, a aplicação aparecerá na aba **Instalados** com atalho direto (URL com porta) e status em tempo real.

### Customização Avançada no Momento da Instalação
Caso queira alterar a porta de acesso (para resolver conflitos) ou alterar diretórios de mídia antes de subir o contêiner:
- Alterne para o modo **Configuração Avançada** no modal.
- Edite os mapeamentos de porta externa (`HOST_PORT:CONTAINER_PORT`).
- Aponte diretórios adicionais de armazenamento (ex: `/tank/media/filmes` ou `/tank/backups`).
- Defina senhas personalizadas para os bancos de dados ou tokens de API.

---

## 4. Integração com Traefik, NPM e Acesso Seguro

O NayBinho NAS já vem pronto para publicação segura de serviços web sem expor portas arbitrárias:

### Descoberta Automática de Roteamento (Traefik)
Os contêineres instalados contêm labels pré-configuradas para o Traefik:
```yaml
labels:
  - "traefik.enable=true"
  - "traefik.http.routers.jellyfin.rule=Host(`jellyfin.local.naybinho.nas`)"
  - "traefik.http.services.jellyfin.loadbalancer.server.port=8096"
```
Com o Traefik ou Nginx Proxy Manager ativo, cada aplicação pode ser acessada por nome amigável (ex: `https://jellyfin.meuhomelab.com`) com certificado SSL Let's Encrypt gerado e renovado automaticamente.

### Acesso Remoto Seguro sem Abertura de Portas (CGNAT / WAN)
Se o seu provedor de internet usa CGNAT (sem IP público IPv4), utilize os apps homologados:
- **Tailscale**: Adiciona o NAS e seus clientes móveis em uma malha VPN WireGuard zero-configuração.
- **Cloudflare Tunnel (`cloudflared`)**: Cria um túnel criptografado de saída para seus domínios públicos sem necessidade de abrir portas 80/443 no roteador residencial.

---

## 5. Transcodificação por Hardware (Intel QuickSync & NVIDIA)

Para contêineres multimídia (Jellyfin, Plex, Emby, Tdarr, Unmanic) ou motores de inteligência artificial (Ollama, Immich), o NayBinho NAS oferece passthrough simplificado de aceleração gráfica:

### Intel QuickSync Video (iGPU)
O dispositivo `/dev/dri` é compartilhado diretamente com o contêiner:
```yaml
devices:
  - /dev/dri:/dev/dri
group_add:
  - "44" # grupo 'video' no Ubuntu 26.04 LTS
  - "107" # grupo 'render'
```
*Vantagem*: Transcodificação de múltiplos streams 4K HDR para 1080p com consumo quase nulo de processamento da CPU.

### NVIDIA Container Toolkit (GPUs Dedicadas)
Quando uma GPU NVIDIA estiver presente no host:
```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: all
          capabilities: [gpu]
```

---

## 6. Gerenciamento e Operação via Linha de Comando (CLI)

Todos os contêineres da App Store respeitam os padrões do Docker Compose e podem ser inspecionados ou manipulados diretamente no terminal do host via SSH:

### Estrutura no Sistema de Arquivos
```
/tank/appdata/
  ├── jellyfin/
  │   ├── docker-compose.yml
  │   ├── config/
  │   └── cache/
  ├── qbittorrent/
  │   ├── docker-compose.yml
  │   └── config/
  └── nextcloud/
      ├── docker-compose.yml
      └── data/
```

### Comandos Essenciais

#### Status e Métricas
```bash
# Listar contêineres ativos com IP e portas
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Consumo de CPU, RAM e I/O de disco em tempo real
docker stats --no-stream
```

#### Operação Direta de um Aplicativo
```bash
cd /tank/appdata/jellyfin

# Reiniciar o serviço
docker compose restart

# Visualizar logs em tempo real
docker compose logs -f --tail=100

# Atualizar para a versão mais recente
docker compose pull && docker compose up -d

# Parar e remover o contêiner sem perder dados
docker compose down
```

#### Manutenção e Limpeza
```bash
# Limpar imagens antigas sem uso e volumes órfãos
docker system prune -a --volumes -f
```

---

## 7. Integração com ZFS: Snapshots Atômicos e Backup

O sistema de arquivos ZFS oferece proteção contra perda de dados e corrupção acidental em atualizações:

1. **Snapshot Pré-Atualização**: Ao atualizar um app pela UI ou via script, um snapshot ZFS é criado automaticamente:
   ```bash
   zfs snapshot tank/appdata/nextcloud@pre-upgrade-$(date +%Y%m%d%H%M)
   ```
2. **Rollback Imediato**: Se uma migração de banco de dados do app falhar:
   ```bash
   docker compose down
   zfs rollback tank/appdata/nextcloud@pre-upgrade-202611130900
   docker compose up -d
   ```
3. **Backup Criptografado Offsite**: Usando o aplicativo **Kopia** ou **Duplicati**, todo o dataset `/tank/appdata` pode ser sincronizado diariamente de forma desduplicada para nuvem (Backblaze B2, Google Drive, Wasabi) ou outro NAS secundário.

---

## 8. Diagnóstico de Problemas e Solução Rápida (Troubleshooting)

### Conflito de Portas no Host
- **Sintoma**: Mensagem `Error response from daemon: driver failed programming external connectivity on endpoint ...: Bind for 0.0.0.0:8080 failed: port is already allocated`.
- **Causa**: Duas aplicações tentando usar a mesma porta TCP externa (ex: qBittorrent e Traefik).
- **Solução**:
  1. Identifique o processo que ocupa a porta: `sudo ss -tulpn | grep 8080`.
  2. Altere o mapeamento `HOST_PORT` no `docker-compose.yml` da aplicação para outra porta livre (ex: `8085:8080`).
  3. Execute `docker compose up -d`.

### Problemas de Permissões em Volumes (`Permission Denied`)
- **Sintoma**: Logs do contêiner indicam que ele não consegue ler ou escrever em `/config` ou `/data`.
- **Solução**: Restaure a titularidade do usuário do NAS (`PUID:PGID 1000:1000`):
  ```bash
  sudo chown -R 1000:1000 /tank/appdata/<app_id>
  sudo chmod -R 775 /tank/appdata/<app_id>
  ```

### Rede Bridge Bloqueada ou Inacessível
- **Solução**: Verifique se a rede `naybinho_network` existe e recrie-a se necessário:
  ```bash
  docker network inspect naybinho_network || docker network create --driver bridge --subnet 172.28.0.0/16 naybinho_network
  ```

---

## 9. Resumo dos Componentes de Código e Arquivos do Módulo

- `appstore/catalog.json`: Catálogo completo com 107 aplicações de Home Lab homologadas.
- `appstore/categories.json`: Definição das 10 categorias oficiais de aplicações.
- `appstore/templates/docker-compose-base.yml`: Template compose base com suporte a healthchecks, Traefik, cgroups e volumes ZFS.
- `docs/DOCKER_GUIDE.md`: Este guia técnico de arquitetura e operação do subsistema Docker.
