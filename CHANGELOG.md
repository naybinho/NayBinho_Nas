# 📋 Histórico de Versões - NayBinho NAS

Todas as versões do **NayBinho NAS** seguem o versionamento semântico (`vMAJOR.MINOR.PATCH`). Abaixo você encontra o detalhamento de cada versão com suas **Novidades**, **Melhorias** e **Correções**.

---

## [v1.0.0] - 2026-11-13 - Lançamento Oficial Inicial

### 🚀 Novidades
- **Base do Sistema Operacional**: Construído sobre o Ubuntu 26.04.1 LTS (Noble Numbat) com kernel otimizado para servidores e Home Lab.
- **Interface Web Moderna**: Painel de controle responsivo com tema Dark Glass, desenvolvido em React 18, Vite, Tailwind CSS e Lucide Icons.
- **Gerenciador de Armazenamento RAID Total**: Suporte a níveis RAID 0, 1, 5, 6 e 10 via `mdadm`, além de integração com ZFS Pools (ZFS raidz1/raidz2).
- **Docker Nativo & Multi-Lojas de Apps**:
  - Loja Oficial Nativa NayBinho
  - CasaOS Play Store (`https://play.cuse.eu.org/store.json`)
  - BigBear CasaOS Store (`https://cdn.jsdelivr.net/gh/bigbeartechworld/big-bear-casaos@gh-pages/store.json`)
  - Zima AppStore (`https://chicohaager.github.io/zima-appstore/store.json`)
  - BigBear CasaOS Master Zip (`https://github.com/bigbeartechworld/big-bear-casaos/archive/refs/heads/master.zip`)
  - Opção no painel para adicionar qualquer URL de repositório de apps ou arquivo ZIP customizado.
- **Compartilhamento de Arquivos em Rede**: Suporte a SMB/CIFS (Windows Shares), NFS e WebDAV diretamente pela interface web.
- **Sistema de Auto-Atualização Integrado**:
  - Verificação automática periódica de novas versões no GitHub Releases.
  - Notificação no cabeçalho e tela do sistema com changelog detalhado de Novidades, Melhorias e Correções.
  - Atualização com 1 clique: download automático, validação SHA256, aplicação de patches e reinicialização dos serviços sem perda de dados.
- **Gerador de Imagem ISO Bootável**: Pipeline automatizado no GitHub Actions para compilação e publicação da ISO com instalador autônomo.

### ⚡ Melhorias
- **Desempenho & Leveza**: Otimização do backend FastAPI assíncrono com baixo consumo de memória RAM (< 150MB no boot).
- **Monitoramento em Tempo Real**: Telemetria ao vivo de CPU, RAM, uso de discos, temperatura e tráfego de rede via WebSockets.
- **Segurança Reforçada**: Autenticação JWT com tokens HttpOnly, hash Argon2 para senhas e controle granular de permissões de usuários.
- **Diagnóstico SMART**: Verificação preventiva da saúde de HDDs e SSDs com alertas de setores defeituosos e temperatura.

### 🐛 Correções
- **Estabilidade de Build**: Correção de resolução de pacotes de interface e compatibilidade com o pipeline do GitHub Actions.
- **Gerenciamento de Discos**: Tratamento de erros na listagem de discos não formatados ou dispositivos de loopback.
- **Docker Daemon**: Ajuste nas permissões do socket do Docker (`/var/run/docker.sock`) para containers gerenciados sem privilégios desnecessários.
