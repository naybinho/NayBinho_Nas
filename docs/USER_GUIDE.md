# 📖 Manual do Usuário — NayBinho NAS

> **Versão:** 1.0.0 | Para suporte técnico avançado, consulte o [ADMIN_GUIDE.md](ADMIN_GUIDE.md)

---

## Índice

1. [Visão Geral da Interface](#1-visão-geral-da-interface)
2. [Dashboard](#2-dashboard)
3. [Gerenciamento de Armazenamento](#3-gerenciamento-de-armazenamento)
4. [RAID](#4-raid)
5. [Compartilhamentos (Shares)](#5-compartilhamentos-shares)
6. [Docker e Loja de Apps](#6-docker-e-loja-de-apps)
7. [Usuários e Grupos](#7-usuários-e-grupos)
8. [Monitoramento](#8-monitoramento)
9. [Configurações do Sistema](#9-configurações-do-sistema)
10. [Notificações](#10-notificações)

---

## 1. Visão Geral da Interface

A interface web do NayBinho NAS é acessada pelo navegador no endereço `http://<ip-do-nas>:8080`.

### Layout Principal

```
┌─────────────────────────────────────────────────────────┐
│  🏠 NayBinho NAS  [Busca...]           🔔  👤 admin  ⚙️  │
├──────────────┬──────────────────────────────────────────┤
│  MENU        │                                          │
│              │          CONTEÚDO PRINCIPAL              │
│  📊 Dashboard│                                          │
│  💾 Storage  │                                          │
│  🔄 RAID     │                                          │
│  📁 Shares   │                                          │
│  🐳 Docker   │                                          │
│  🛒 Apps     │                                          │
│  👥 Usuários │                                          │
│  📈 Monitor  │                                          │
│  ⚙️ Config   │                                          │
└──────────────┴──────────────────────────────────────────┘
```

### Barra de Navegação Superior
- **Logo/Home:** Clique para retornar ao Dashboard
- **Busca:** Pesquise por configurações, apps, discos
- **🔔 Notificações:** Badge com número de alertas não lidos
- **👤 Perfil:** Configurações do usuário, logout
- **⚙️ Configurações rápidas**

---

## 2. Dashboard

O Dashboard é a tela inicial e apresenta uma visão geral do sistema em tempo real.

### Widgets Disponíveis

#### Cards de Status Rápido
- **CPU:** Uso percentual com gráfico sparkline
- **RAM:** Uso e total disponível
- **Temperatura:** Temperatura do processador
- **Uptime:** Tempo desde o último boot

#### Gráficos em Tempo Real
- **CPU %** — Atualizado a cada 2 segundos via WebSocket
- **RAM %** — Uso de memória ao longo do tempo
- **Rede (↑↓)** — Taxa de upload e download por interface
- **I/O de Disco** — Leitura e escrita em tempo real

#### Painel de Armazenamento
- Discos detectados com capacidade e status
- Arrays RAID ativos com estado de saúde (OK / Degradado / Falho)
- Espaço total vs. usado (gráfico de rosca)

#### Containers Docker Ativos
- Lista dos últimos 5 containers com status (running/stopped)
- Ação rápida: iniciar/parar/reiniciar

#### Alertas Recentes
- Últimos 5 alertas do sistema com severidade colorida

### Personalizando o Dashboard
1. Clique no ícone **⚙️** no canto superior direito do Dashboard
2. Arraste e solte os widgets para reorganizá-los
3. Ative/desative widgets usando os toggles
4. Clique em **"Salvar Layout"**

---

## 3. Gerenciamento de Armazenamento

### 3.1 Visualizando Discos

Vá em **Storage → Discos** para ver todos os discos conectados.

Para cada disco são exibidos:
- **Modelo e Fabricante** (ex: Seagate IronWolf 4TB)
- **Serial Number**
- **Tamanho**
- **Interface** (SATA, NVMe, SAS)
- **Temperatura** (°C)
- **Status SMART** (Aprovado / Atenção / Falho)
- **Horas de uso**

### 3.2 Relatório SMART

1. Clique no disco desejado
2. Selecione a aba **"SMART"**
3. Veja o relatório completo com todos os atributos
4. Atributos críticos monitorados:
   - `Reallocated_Sector_Ct` — setores realocados (> 0 = atenção)
   - `Current_Pending_Sector` — setores pendentes
   - `Offline_Uncorrectable` — erros não corrigíveis
   - `Temperature_Celsius` — temperatura atual

### 3.3 Volumes e Sistemas de Arquivos

**Storage → Volumes**

| Coluna | Descrição |
|---|---|
| Nome | Identificador do volume |
| Tipo | ext4, XFS, ZFS, Btrfs |
| Tamanho | Capacidade total |
| Usado | Espaço ocupado |
| Disponível | Espaço livre |
| Ponto de Montagem | Caminho no sistema |

#### Formatar um disco
> ⚠️ **ATENÇÃO: Essa operação apaga TODOS os dados do disco!**

1. Vá em **Storage → Discos**
2. Clique no disco a formatar
3. Clique em **"Formatar"**
4. Escolha o sistema de arquivos:
   - **ext4** — Padrão Linux, compatível, estável
   - **XFS** — Melhor para arquivos grandes
   - **ZFS** — Pool com snapshots, checksums, compressão
   - **Btrfs** — Snapshots, subvolumes
5. Digite `CONFIRMAR` no campo de confirmação
6. Clique em **"Executar Formatação"**

---

## 4. RAID

### 4.1 Tipos de RAID Suportados

| RAID | Mín. Discos | Falhas Toleradas | Uso Recomendado |
|---|---|---|---|
| **RAID 0** | 2 | 0 | Performance, sem redundância |
| **RAID 1** | 2 | 1 | Espelhamento simples |
| **RAID 5** | 3 | 1 | Equilíbrio entre espaço e redundância |
| **RAID 6** | 4 | 2 | Alta disponibilidade |
| **RAID 10** | 4 | 1 por espelho | Alta performance + redundância |

### 4.2 Criando um Array RAID

1. Vá em **Storage → RAID → "+ Novo RAID"**
2. Preencha:
   - **Nome:** Identificador (ex: `md0`, `dados`, `backup`)
   - **Nível RAID:** Selecione o tipo
   - **Discos:** Marque os discos que farão parte do array
   - **Sistema de Arquivos:** ext4, XFS ou ZFS
   - **Ponto de Montagem:** Onde será montado (ex: `/mnt/dados`)
3. Clique em **"Criar RAID"**
4. Aguarde a sincronização inicial (pode levar horas para discos grandes)

> **Dica:** Acompanhe o progresso de sincronização em **Storage → RAID → [nome do array] → Status**

### 4.3 Monitorando a Saúde do RAID

Indicadores de status:

| Status | Cor | Significado |
|---|---|---|
| ✅ Ativo | Verde | Array funcionando normalmente |
| ⚠️ Degradado | Amarelo | Um disco falhou, funcionando com redundância reduzida |
| 🔄 Reconstruindo | Azul | Reconstruindo após substituição de disco |
| ❌ Falho | Vermelho | Array inoperante, ação imediata necessária |

### 4.4 Substituindo um Disco Falho

1. Identifique o disco falho em **Storage → RAID**
2. **Remova** o disco falho do array: clique em **"Remover Disco"**
3. Fisicamente substitua o disco no servidor
4. Vá em **Storage → RAID → [array] → "Adicionar Disco"**
5. Selecione o novo disco
6. O NayBinho NAS iniciará a reconstrução automaticamente

---

## 5. Compartilhamentos (Shares)

### 5.1 Compartilhamento SMB (Windows/macOS)

#### Criar um Compartilhamento SMB

1. Vá em **Shares → SMB → "+ Novo Share"**
2. Configure:
   - **Nome:** Nome visível na rede (ex: `Fotos`, `Filmes`, `Backup`)
   - **Caminho:** Pasta no servidor (ex: `/mnt/dados/fotos`)
   - **Comentário:** Descrição opcional
   - **Visível:** Se aparece ao navegar na rede
   - **Acesso para Convidados:** Permitir/Negar acesso sem senha
3. **Permissões:**
   - Adicione usuários e grupos com nível de acesso (Leitura / Leitura+Escrita / Administrador)
4. **Avançado (opcional):**
   - Recycle Bin (lixeira de rede)
   - Auditoria de acesso
   - Quota de disco
5. Clique em **"Criar"**

#### Acessar pelo Windows

```
\\192.168.1.100\NomeDoShare
ou
\\naybinho-nas\NomeDoShare
```

No Windows Explorer, pressione `Win + R`, digite o endereço acima.

#### Acessar pelo macOS

No Finder: **Ir → Conectar ao Servidor** → `smb://192.168.1.100/NomeDoShare`

### 5.2 Compartilhamento NFS (Linux)

#### Criar um Compartilhamento NFS

1. Vá em **Shares → NFS → "+ Novo Export"**
2. Configure:
   - **Caminho:** Pasta exportada (ex: `/mnt/dados`)
   - **Clientes Permitidos:** IP ou range CIDR (ex: `192.168.1.0/24` ou `*` para todos)
   - **Opções:**
     - `rw` / `ro` — Leitura+Escrita / Somente Leitura
     - `sync` / `async` — Escrita síncrona/assíncrona
     - `no_subtree_check` — Desabilitar verificação de subárvore
     - `no_root_squash` — Manter permissões de root (cuidado!)
3. Clique em **"Exportar"**

#### Montar no Linux Cliente

```bash
# Instalar cliente NFS
sudo apt install nfs-common

# Montar o share
sudo mount -t nfs 192.168.1.100:/mnt/dados /mnt/nas

# Montar permanentemente (adicionar ao /etc/fstab)
192.168.1.100:/mnt/dados  /mnt/nas  nfs  defaults,_netdev  0  0
```

---

## 6. Docker e Loja de Apps

### 6.1 Docker Manager

Vá em **Docker** para gerenciar containers:

#### Containers
- **Listar** todos os containers (rodando e parados)
- **Iniciar / Parar / Reiniciar / Remover**
- Ver **logs** em tempo real
- Ver **stats** (CPU, RAM, rede, I/O)
- Acessar **terminal** (exec) no container

#### Imagens
- Listar imagens baixadas
- **Pull** de nova imagem (ex: `nginx:latest`)
- Remover imagens não utilizadas

#### Redes e Volumes Docker
- Criar/remover redes Docker
- Gerenciar volumes persistentes

### 6.2 Loja de Apps

A Loja de Apps oferece aplicativos pré-configurados prontos para instalar com 1 clique.

#### Categorias de Apps

| Categoria | Exemplos |
|---|---|
| 📺 Mídia | Plex, Jellyfin, Emby, Navidrome |
| 📥 Downloads | qBittorrent, SABnzbd, Sonarr, Radarr |
| 🏠 Smart Home | Home Assistant, Mosquitto |
| 🔐 Segurança | Vaultwarden, Authelia |
| 🗄️ Banco de Dados | PostgreSQL, MariaDB, Redis |
| ☁️ Cloud Pessoal | Nextcloud, Seafile |
| 📊 Monitoramento | Grafana, Prometheus, Netdata |
| 🌐 Web | Nginx, Traefik, Caddy |

#### Instalando um App

1. Vá em **Apps → Loja**
2. Navegue por categorias ou use a busca
3. Clique no app desejado
4. Veja a descrição, versão, requisitos e portas
5. Configure as variáveis (volumes, portas, variáveis de ambiente)
6. Clique em **"Instalar"**
7. O NayBinho NAS fará o pull da imagem e iniciará o container automaticamente

#### Atualizando Apps

1. Vá em **Apps → Instalados**
2. Se há atualização disponível, aparecerá um badge **"Atualização"**
3. Clique em **"Atualizar"** para baixar a nova imagem e recriar o container

---

## 7. Usuários e Grupos

### 7.1 Criando Usuários

1. Vá em **Usuários → "+ Novo Usuário"**
2. Preencha:
   - **Nome de usuário:** login (ex: `joao`, `maria`)
   - **Nome completo:** Nome exibido
   - **Email:** Para notificações
   - **Senha:** Defina ou gere aleatoriamente
   - **Grupos:** Adicione a grupos existentes
   - **Acesso à Interface Web:** Sim/Não
   - **Cota de disco:** Limite de espaço (opcional)
3. Clique em **"Criar Usuário"**

### 7.2 Grupos

Grupos facilitam o gerenciamento de permissões em compartilhamentos:

| Grupo Padrão | Descrição |
|---|---|
| `admins` | Acesso total à interface e ao sistema |
| `users` | Usuários padrão |
| `readonly` | Acesso somente leitura aos shares |

Crie grupos personalizados em **Usuários → Grupos → "+ Novo Grupo"**.

---

## 8. Monitoramento

### 8.1 Métricas em Tempo Real

**Monitoramento → Tempo Real**

- Gráficos ao vivo via WebSocket
- CPU, RAM, Swap, Rede (por interface), I/O de disco (por disco)
- Atualização a cada 2 segundos

### 8.2 Histórico de Métricas

**Monitoramento → Histórico**

Selecione o período:
- Última hora
- Últimas 6 horas
- Últimas 24 horas
- Últimos 7 dias
- Últimos 30 dias

### 8.3 Alertas

**Monitoramento → Alertas**

Thresholds padrão configuráveis:

| Métrica | Aviso | Crítico |
|---|---|---|
| CPU % | 80% | 95% |
| RAM % | 85% | 95% |
| Temperatura | 70°C | 85°C |
| Disco usado % | 80% | 90% |
| SMART status | — | Falha detectada |

### 8.4 Logs

**Monitoramento → Logs**

- Filtre por serviço (sistema, samba, nfs, docker, etc.)
- Filtre por nível (info, warning, error, critical)
- Busca em tempo real
- Exportar logs para arquivo

---

## 9. Configurações do Sistema

### 9.1 Geral

**Configurações → Geral**
- Hostname do servidor
- Fuso horário
- Idioma da interface
- NTP (servidores de tempo)

### 9.2 Rede

**Configurações → Rede**

Consulte o [NETWORK_GUIDE.md](NETWORK_GUIDE.md) para configurações detalhadas de:
- IP estático / DHCP
- VLANs
- Bonding (agregação de links)
- DNS

### 9.3 Atualização do Sistema

**Configurações → Atualização**

- Ver versão atual do NayBinho NAS
- Verificar atualizações disponíveis
- Aplicar atualizações (requer reinicialização em alguns casos)
- Configurar atualização automática (horário agendado)

### 9.4 Certificado SSL

**Configurações → SSL/TLS**

- Instalar certificado Let's Encrypt (domínio público)
- Importar certificado personalizado
- Usar certificado autoassinado (padrão)

Após configurar SSL, acesse via `https://` na porta 8443.

### 9.5 SSH

**Configurações → SSH**

- Habilitar/desabilitar acesso SSH
- Porta SSH (padrão: 22)
- Autenticação por chave pública
- Desabilitar autenticação por senha (recomendado para segurança)

---

## 10. Notificações

### Canais de Notificação Suportados

| Canal | Configuração |
|---|---|
| **Email** | SMTP: servidor, porta, usuário, senha, TLS |
| **Telegram** | Bot Token + Chat ID |
| **Slack** | Webhook URL |
| **Discord** | Webhook URL |
| **Pushover** | API Key + User Key |
| **Webhook** | URL customizada com payload JSON |

### Configurando Notificações

1. Vá em **Configurações → Notificações**
2. Clique em **"+ Adicionar Canal"**
3. Selecione o tipo e preencha as credenciais
4. Clique em **"Testar"** para verificar se está funcionando
5. Clique em **"Salvar"**

### Tipos de Eventos Notificáveis

- Falha de disco (SMART)
- RAID degradado/falho
- CPU/RAM/Temperatura crítica
- Disco quase cheio
- Atualização disponível
- Login de usuário
- Erro de serviço
- Conclusão de backup

---

*Para mais informações, consulte [FAQ.md](FAQ.md) ou abra uma issue no GitHub.*
