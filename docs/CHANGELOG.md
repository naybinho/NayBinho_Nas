# 📜 Histórico de Versões (CHANGELOG) — NayBinho NAS

Todas as mudanças notáveis no projeto **NayBinho NAS** estão documentadas neste arquivo.
O formato é baseado no [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/) e este projeto segue o [Semantic Versioning](https://semver.org/lang/pt-BR/).

---

## [1.0.0] — 2026-11-13 — *Versão Estável Oficial (Lançamento)*

### 🎉 Destaques do Lançamento
- Sistema operacional completo e autônomo baseado no **Ubuntu 26.04.1 LTS**.
- Interface web responsiva em **React 18 + TypeScript + TailwindCSS + Lucide Icons**.
- Backend de alta performance em **FastAPI (Python 3.12)** com suporte a WebSockets e SSE.
- Gerenciamento simplificado de arrays **RAID 0, 1, 5, 6 e 10** com monitoramento em tempo real.
- Loja de Aplicativos (App Store) com mais de 50 containers Docker pré-configurados.

### Adicionado
- **Wizard de Primeiro Acesso:** Assistente interativo para definição de hostname, timezone, senha de admin e rede.
- **Gerenciador de Compartilhamentos:**
  - Painel completo para configuração de **Samba (SMB)** com suporte a lixeira de rede (`vfs_recycle`) e ACLs.
  - Painel de exportações **NFS (v3/v4.2)** com suporte a filtragem granular por cliente e sub-redes.
  - Endpoint de teste de conectividade para shares de rede.
- **Centro de Notificações Multi-canal:**
  - Envio de alertas de saúde do sistema via Telegram, Discord, Slack, Email (SMTP) e Pushover.
  - Registro interno de notificações não lidas e histórico de avisos críticos.
- **Monitoramento e Diagnóstico:**
  - Gráficos em tempo real de CPU, memória, I/O de disco e tráfego de rede via WebSocket `/ws/stats`.
  - Testes e relatórios de saúde de disco com atributos **SMART** detalhados.
  - Gerador automatizado de relatórios de diagnóstico do sistema (`diagnostic-report.sh`).
- **Backup e Restauração:**
  - Backup automatizado das configurações do sistema em arquivos compactados `.tar.gz`.
  - Restauração com 1 clique pela interface gráfica ou CLI.
- **Documentação Completa:**
  - Guia de Instalação (`INSTALL_GUIDE.md`).
  - Manual do Usuário (`USER_GUIDE.md`).
  - Guia do Administrador (`ADMIN_GUIDE.md`).
  - Guia de Redes e LACP (`NETWORK_GUIDE.md`).
  - Guia de Compartilhamento de Arquivos (`SHARING_GUIDE.md`).
  - FAQ detalhado com mais de 35 perguntas e respostas (`FAQ.md`).

---

## [0.9.0-rc1] — 2026-10-25 — *Release Candidate*

### Adicionado
- Gerenciamento de rede avançado: suporte a VLANs (802.1Q) e Link Aggregation / Bonding (LACP 802.3ad e active-backup).
- Mecanismo de rollback automático para configurações de rede com timeout de segurança de 30 segundos.
- Suporte inicial a pools ZFS com criação de datasets e snapshots periódicos.
- Visualizador de logs com filtragem em tempo real e pesquisa de texto.

### Modificado
- Reformulação visual completa do Dashboard com personalização de widgets em grid.
- Melhoria na velocidade de sincronização inicial de arrays RAID via tuning do `/proc/sys/dev/raid/speed_limit_max`.

### Corrigido
- Correção de falha no Samba que impedia clientes Windows 11 de autenticarem sem credenciais legadas NTLMv1.
- Correção de vazamento de descritores de arquivo no WebSocket de monitoramento de métricas.

---

## [0.8.0] — 2026-09-15 — *Docker & App Store*

### Adicionado
- Gerenciador Docker integrado: listar, iniciar, parar, reiniciar containers e visualizar logs.
- Suporte a `docker-compose.yml` diretamente pela interface web.
- Integração da App Store com categorias (Mídia, Home Lab, Segurança, Downloads, Banco de Dados).
- Suporte a aceleração de hardware (Intel QuickSync / VA-API) nos templates de containers multimídia (Jellyfin e Plex).

### Modificado
- As rotas da API REST foram modularizadas em routers independentes (`routers/docker_manager.py`, `routers/apps_store.py`).

---

## [0.6.0] — 2026-08-01 — *Storage & RAID Engine*

### Adicionado
- Módulo de gerenciamento de discos físicos com identificação de serial, modelo, tipo de barramento e temperatura.
- Criação e destruição de volumes RAID via chamadas nativas ao `mdadm`.
- Leitura automatizada do `/proc/mdstat` para exibição de progresso percentual de reconstrução e verificação.
- Formatação de partições em sistemas de arquivos ext4 e XFS.

---

## [0.4.0] — 2026-06-20 — *Backend & Core Architecture*

### Adicionado
- Servidor FastAPI com autenticação JWT (JSON Web Tokens) e controle de sessões.
- Banco de dados SQLite interno com SQLAlchemy ORM para configurações de usuários e preferências.
- Integração com `systemd` para inicialização automática do serviço `naybinho-api.service`.
- Coleta de métricas do sistema com a biblioteca `psutil`.

---

## [0.2.0] — 2026-05-10 — *Base do Sistema Operacional & Build ISO*

### Adicionado
- Scripts automatizados para geração da ISO personalizada baseada no Ubuntu 26.04.1 LTS (`build-iso.sh`).
- Configuração de boot loader GRUB com tema visual personalizado do NayBinho NAS.
- Preseed / autoinstall para particionamento e instalação desassistida do sistema.
- Inclusão dos pacotes essenciais: `samba`, `nfs-kernel-server`, `mdadm`, `smartmontools`, `docker.io`, `zfsutils-linux`.

---

## [0.1.0] — 2026-04-01 — *Concepção do Projeto (Alpha)*

### Adicionado
- Especificação da arquitetura inicial do NayBinho NAS.
- Definição do escopo: SO leve, gratuito e amigável para home labs.
- Criação do repositório de código e planejamento das metas de entrega.
