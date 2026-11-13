# 📂 Guia de Compartilhamentos (Shares) — NayBinho NAS

> **Versão:** 1.0.0 | **Protocolos:** SMB (Samba 4.x), NFS (v3 / v4.2)

---

## Índice

1. [Introdução](#1-introdução)
2. [Samba / SMB (Windows, macOS, Linux, Mobile)](#2-samba--smb-windows-macos-linux-mobile)
3. [NFS (Linux, Proxmox, VMware, Kubernetes)](#3-nfs-linux-proxmox-vmware-kubernetes)
4. [Permissões de Arquivos e Pastas (POSIX e ACLs)](#4-permissões-de-arquivos-e-pastas-posix-e-acls)
5. [Lixeira de Rede (Recycle Bin)](#5-lixeira-de-rede-recycle-bin)
6. [Otimização de Desempenho](#6-otimização-de-desempenho)
7. [Boas Práticas de Segurança](#7-boas-práticas-de-segurança)
8. [Troubleshooting de Compartilhamentos](#8-troubleshooting-de-compartilhamentos)

---

## 1. Introdução

O NayBinho NAS centraliza seus dados e disponibiliza armazenamento através dos dois protocolos de rede mais utilizados no mundo:
- **SMB (Server Message Block / CIFS):** Padrão do Windows, perfeitamente suportado no macOS e compatível com smartphones, Smart TVs e Linux.
- **NFS (Network File System):** Altamente performático e nativo para estações de trabalho Linux, servidores de virtualização (Proxmox VE, VMware ESXi) e clusters de containers.

---

## 2. Samba / SMB (Windows, macOS, Linux, Mobile)

### 2.1 Criando um Compartilhamento SMB

1. No painel de navegação esquerdo, clique em **Shares → SMB**.
2. Clique em **"+ Novo Compartilhamento SMB"**.
3. Preencha os campos obrigatórios:
   - **Nome do Share:** Ex: `Documentos`, `Projetos`, `Midia`. Este é o nome exibido na rede.
   - **Caminho no Sistema:** Diretório absoluto montado no NAS (ex: `/mnt/dados/documentos`). Se a pasta não existir, marque a opção *Criar pasta automaticamente*.
   - **Comentário / Descrição:** Texto explicativo sobre o conteúdo.
4. Ajuste as opções de visibilidade e acesso:
   - **Navegável (Browseable):** Permite que o share apareça na lista de rede do Windows/Mac.
   - **Permitir Convidados (Guest Ok):** Se ativado, qualquer pessoa na rede local poderá ler ou escrever sem senha. *(Desative em ambientes com dados confidenciais)*.
   - **Somente Leitura (Read Only):** Bloqueia alterações de arquivos mesmo para usuários autenticados.
5. Selecione os usuários e grupos com permissão de acesso e escrita.
6. Clique em **Salvar**. O Samba recarrega as configurações instantaneamente sem derrubar outras sessões ativas.

### 2.2 Conectando a partir de Clientes

#### No Windows 10 / 11
1. Abra o **Explorador de Arquivos**.
2. Na barra de endereço, digite:
   ```
   \\192.168.1.100\Documentos
   # ou usando o hostname:
   \\naybinho-nas\Documentos
   ```
3. Pressione Enter. Se solicitado, insira seu usuário e senha cadastrados no NayBinho NAS.
4. **Mapear Unidade de Rede (Letra fixa como Z:):**
   - Clique com o botão direito em *Este Computador* → *Mapear unidade de rede...*
   - Escolha a letra (ex: `Z:`) e informe o caminho `\\192.168.1.100\Documentos`.
   - Marque *Reconectar ao entrar*.

#### No Apple macOS
1. No menu superior do **Finder**, clique em **Ir (Go)** → **Conectar ao Servidor (Connect to Server)** (ou atalho `Cmd + K`).
2. Digite:
   ```
   smb://192.168.1.100/Documentos
   ```
3. Clique em **Conectar**, escolha *Usuário Registrado* e informe suas credenciais.

#### No Linux Desktop (GNOME / KDE)
- No gerenciador de arquivos (Nautilus/Dolphin), vá em *Outros Locais* → *Conectar ao Servidor*.
- Digite: `smb://192.168.1.100/Documentos`.

#### Em Dispositivos Móveis (Android / iOS)
- No iOS: Use o aplicativo nativo **Arquivos** → `...` → **Conectar ao Servidor** → `smb://192.168.1.100`.
- No Android: Utilize apps como **CX File Explorer**, **Solid Explorer** ou **VLC**.

---

## 3. NFS (Linux, Proxmox, VMware, Kubernetes)

NFS oferece overhead mínimo e alta vazão para sistemas baseados em Unix.

### 3.1 Criando um Compartilhamento NFS

1. Acesse **Shares → NFS**.
2. Clique em **"+ Novo Export NFS"**.
3. Preencha as configurações:
   - **Caminho do Diretório:** Ex: `/mnt/dados/backups-proxmox`.
   - **Hosts / Clientes Permitidos:**
     - Uma máquina específica: `192.168.1.50`
     - Toda a sub-rede local: `192.168.1.0/24`
     - Qualquer host: `*` (apenas para redes totalmente isoladas)
   - **Modo de Acesso:** `rw` (Leitura e Escrita) ou `ro` (Somente Leitura).
   - **Sincronismo:**
     - `sync` (Padrão e Seguro): O servidor responde que a gravação terminou apenas após gravar no disco físico.
     - `async`: Mais veloz, porém com risco de corrupção caso ocorra queda de energia antes da sincronização dos buffers.
   - **Mapeamento de Root (Root Squashing):**
     - `root_squash` (Recomendado): O usuário `root` do cliente é mapeado para o usuário anônimo `nobody`.
     - `no_root_squash`: Necessário para datastores Proxmox/VMware onde o hypervisor precisa criar arquivos como root.
4. Clique em **Salvar Export**.

### 3.2 Montando no Cliente Linux / Hypervisor

#### Montagem Manual Temporária

```bash
# Certifique-se de ter o utilitário montador instalado
sudo apt install -y nfs-common   # Debian/Ubuntu
sudo dnf install -y nfs-utils    # RHEL/Fedora

# Criar ponto de montagem e montar
sudo mkdir -p /mnt/nas-nfs
sudo mount -t nfs -o proto=tcp,port=2049 192.168.1.100:/mnt/dados/backups-proxmox /mnt/nas-nfs
```

#### Montagem Persistente via `/etc/fstab`

Edite `/etc/fstab` no servidor cliente adicionando a linha:

```text
192.168.1.100:/mnt/dados/backups-proxmox  /mnt/nas-nfs  nfs  defaults,_netdev,auto,nofail  0  0
```

---

## 4. Permissões de Arquivos e Pastas (POSIX e ACLs)

Para evitar erros de permissão negada (`Permission Denied`), o NayBinho NAS integra as permissões do sistema operacional com os usuários de rede:

1. **Permissões POSIX Padrão:** Cada pasta possui Dono (Owner), Grupo (Group) e Outros (Others) com direitos de Leitura (`r`), Escrita (`w`) e Execução/Navegação (`x`).
2. **Propriedade Padrão:** Os shares SMB gravam arquivos herdando o grupo principal do compartilhamento com permissão de criação `0664` (arquivos) e `0775` (pastas).
3. **Redefinir Permissões Recursivas:**
   - No painel, na tela de edição do Share, existe o botão **"Corrigir Permissões Recursivas"**.
   - Isso ajusta todo o conteúdo interno da pasta para pertencer ao usuário e grupo definidos, solucionando conflitos após migrações de dados externas.

---

## 5. Lixeira de Rede (Recycle Bin)

Para evitar desastres provocados pela exclusão acidental de arquivos via rede (já que a tecla `Delete` no Windows costuma apagar compartilhamentos de rede sem passar pela lixeira local do Windows):

1. Na edição do Compartilhamento SMB, marque a opção **Habilitar Lixeira de Rede (Recycle Bin)**.
2. Nome da pasta oculta: `.recycle`.
3. Quando um usuário apagar um arquivo, ele será movido instantaneamente para a pasta `.recycle` dentro do share.
4. Você pode configurar uma tarefa cron em **Configurações → Tarefas Agendadas** para expurgar arquivos da lixeira com mais de 30 dias automaticamente:
   ```bash
   find /mnt/dados/*/.recycle/ -type f -mtime +30 -delete
   ```

---

## 6. Otimização de Desempenho

O NayBinho NAS já vem com perfis de tuning pré-configurados no arquivo do Samba (`smb.conf`):

```ini
[global]
   socket options = TCP_NODELAY IPTOS_LOWDELAY SO_RCVBUF=131072 SO_SNDBUF=131072
   aio read size = 16384
   aio write size = 16384
   use sendfile = yes
   strict locking = no
   min receivefile size = 16384
```

- **Placas 2.5GbE e 10GbE:** Habilite **Jumbo Frames (MTU 9000)** na sua placa de rede e no switch para atingir taxas de transferência acima de 1.100 MB/s.
- **Multichannel SMB:** Pode ser ativado em **Shares → SMB → Configurações Globais → Habilitar SMB Multichannel**. Se você possui 2 placas de rede de 1 Gbps, o Samba agregará a velocidade atingindo ~220 MB/s sem necessidade de switch LACP.

---

## 7. Boas Práticas de Segurança

1. **Desative SMBv1:** O protocolo SMBv1 é vulnerável a malwares como WannaCry. O NayBinho NAS desabilita SMBv1 por padrão, utilizando apenas **SMBv2.1** e **SMBv3.1.1**.
2. **Criptografia de Transporte:** Para conexões críticas, ative a opção *Forçar Criptografia SMB* nas configurações avançadas do share.
3. **Limite de Acesso por Sub-rede:** Em ambientes corporativos, restrinja o acesso a shares administrativos permitindo apenas IPs confiáveis (ex: `hosts allow = 192.168.1.50, 192.168.1.51`).

---

## 8. Troubleshooting de Compartilhamentos

| Sintoma | Causa Mais Frequente | Como Resolver |
|---|---|---|
| Windows dá erro "Caminho de rede não encontrado" | Firewall bloqueando porta 445 ou nome não resolve | Teste pelo IP (`\\192.168.1.100\share`) e verifique `sudo ufw status` |
| Erro "Acesso negado" ao tentar gravar | Permissão POSIX no Linux não concede escrita | Clique em "Corrigir Permissões" na interface ou execute `sudo chmod -R 775 /caminho` |
| Share não aparece na rede ("Ambiente de Rede") | Serviço Avahi/WSDD desativado | No painel, confirme se o serviço **WS-Discovery** está em execução |
| Lentidão no macOS ao abrir pastas grandes | Geração de arquivos `.DS_Store` e metadados | Ative a opção *Compatibilidade macOS (vfs_fruit)* no share |
| NFS responde `Permission Denied` no cliente | Mapeamento de UID/GID diferente ou IP incorreto | Verifique se o IP do cliente está na lista de hosts permitidos do export |
