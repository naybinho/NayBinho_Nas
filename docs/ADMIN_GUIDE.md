# 🛠️ Guia do Administrador — NayBinho NAS

> **Versão:** 1.0.0 | Para instalação, consulte [INSTALL_GUIDE.md](INSTALL_GUIDE.md)

---

## Índice

1. [Acesso Administrativo](#1-acesso-administrativo)
2. [Backup](#2-backup)
3. [Restauração (Restore)](#3-restauração-restore)
4. [Manutenção do Sistema](#4-manutenção-do-sistema)
5. [Segurança](#5-segurança)
6. [Troubleshooting](#6-troubleshooting)
7. [Logs e Diagnóstico](#7-logs-e-diagnóstico)
8. [Recuperação de Desastres](#8-recuperação-de-desastres)

---

## 1. Acesso Administrativo

### Interface Web

Acesse `http://<ip>:8080` com as credenciais de administrador.

### Acesso SSH

```bash
ssh admin@192.168.1.100

# Ou com chave pública
ssh -i ~/.ssh/id_rsa admin@192.168.1.100
```

### Console Local

Pressione `Alt+F2` para acessar o console virtual durante o boot ou conecte um monitor/teclado diretamente ao servidor.

### Usuário Root

O NayBinho NAS usa `sudo` para operações privilegiadas. O usuário `admin` tem permissão sudo completa:

```bash
sudo su -   # Acessa o shell root
sudo systemctl status naybinho-api   # Exemplo com sudo
```

---

## 2. Backup

### 2.1 Backup das Configurações do NayBinho NAS

As configurações do sistema estão em `/etc/naybinho/`. Faça backup regularmente:

#### Via Interface Web

1. Vá em **Configurações → Backup → "Backup de Configurações"**
2. Clique em **"Gerar Backup"**
3. Faça o download do arquivo `.tar.gz`
4. Guarde em local seguro (externo ao NAS)

#### Via CLI

```bash
# Backup das configurações
sudo /opt/naybinho/scripts/backup-config.sh

# O arquivo será salvo em /var/backups/naybinho/
ls -lh /var/backups/naybinho/
```

Conteúdo do backup de configurações:
```
naybinho-config-2026-11-13.tar.gz
├── /etc/naybinho/          # Configurações principais
├── /etc/samba/smb.conf     # Configuração SMB
├── /etc/exports            # Configuração NFS
├── /etc/netplan/           # Configuração de rede
└── naybinho.db             # Banco de dados SQLite
```

### 2.2 Backup de Dados

#### Rsync (Local ou Remoto)

```bash
# Backup local para outro disco
rsync -avz --progress /mnt/dados/ /mnt/backup/dados/

# Backup remoto via SSH
rsync -avz --progress -e ssh /mnt/dados/ user@servidor-remoto:/backup/nas/

# Backup com exclusões
rsync -avz --exclude='*.tmp' --exclude='Thumbs.db' \
  /mnt/dados/ /mnt/backup/

# Backup incremental com link-dest (economiza espaço)
DATE=$(date +%Y-%m-%d)
rsync -avz --link-dest=/mnt/backup/latest \
  /mnt/dados/ /mnt/backup/$DATE/
ln -sfn /mnt/backup/$DATE /mnt/backup/latest
```

#### Backup Agendado (Cron)

```bash
sudo crontab -e

# Exemplo: backup diário às 2h da manhã
0 2 * * * rsync -avz /mnt/dados/ /mnt/backup/dados/ >> /var/log/naybinho/backup.log 2>&1
```

#### Via Interface Web (Scheduled Backup)

1. Vá em **Configurações → Backup → Agendamentos**
2. Clique em **"+ Novo Agendamento"**
3. Configure:
   - **Origem:** Pasta de origem
   - **Destino:** Pasta/disco destino ou servidor remoto (SSH)
   - **Frequência:** Horária, Diária, Semanal, Mensal
   - **Hora de execução**
   - **Retenção:** Quantidade de backups a manter
4. Clique em **"Salvar"**

### 2.3 Snapshots ZFS

Se estiver usando ZFS, aproveite os snapshots:

```bash
# Criar snapshot
zfs snapshot pool/dados@backup-$(date +%Y%m%d)

# Listar snapshots
zfs list -t snapshot

# Comparar snapshot com atual
zfs diff pool/dados@backup-20261113 pool/dados

# Deletar snapshot antigo
zfs destroy pool/dados@backup-20261001
```

#### Automatizar Snapshots ZFS

```bash
# Instalar zfs-auto-snapshot (já incluído no NayBinho NAS)
sudo apt install zfs-auto-snapshot

# Configurar (editar frequências)
sudo systemctl enable zfs-auto-snapshot@hourly.service
sudo systemctl enable zfs-auto-snapshot@daily.service
```

### 2.4 Backup para Nuvem

O NayBinho NAS suporta backup para:

| Provedor | Ferramenta | Configuração |
|---|---|---|
| AWS S3 | rclone | `rclone config` |
| Google Drive | rclone | `rclone config` |
| Backblaze B2 | rclone | `rclone config` |
| OneDrive | rclone | `rclone config` |
| Qualquer S3-compat. | rclone | `rclone config` |

```bash
# Exemplo: backup para Backblaze B2
rclone sync /mnt/dados/ b2:meu-bucket-nas/ \
  --progress \
  --transfers 4 \
  --log-file /var/log/naybinho/rclone.log
```

---

## 3. Restauração (Restore)

### 3.1 Restaurar Configurações

#### Via Interface Web

1. Vá em **Configurações → Backup → "Restaurar Configurações"**
2. Clique em **"Selecionar arquivo"** e escolha o `.tar.gz`
3. Clique em **"Restaurar"**
4. O sistema aplicará as configurações e solicitará reinicialização

#### Via CLI

```bash
# Restaurar backup de configurações
sudo /opt/naybinho/scripts/restore-config.sh /var/backups/naybinho/naybinho-config-2026-11-13.tar.gz

# Reiniciar serviços
sudo systemctl restart naybinho-api
sudo systemctl restart smbd nmbd
sudo systemctl restart nfs-server
```

### 3.2 Restaurar Dados

```bash
# Restaurar com rsync (preserva permissões)
rsync -avz --progress /mnt/backup/dados/ /mnt/dados/

# Restaurar arquivo específico
rsync -avz /mnt/backup/dados/documentos/arquivo.pdf /mnt/dados/documentos/

# Restaurar de snapshot ZFS
zfs rollback pool/dados@backup-20261113
```

### 3.3 Restauração Completa do Sistema

Em caso de falha catastrófica (disco do sistema corrompido):

1. **Reinstale o NayBinho NAS** via ISO (os discos de dados não são afetados)
2. **Acesse a interface web** e complete o wizard básico
3. **Restaure as configurações** via **Configurações → Backup → Restaurar**
4. Os compartilhamentos, usuários e configurações de rede serão restaurados automaticamente
5. Os dados nos discos de dados permanecem intactos (o sistema está em disco separado)

---

## 4. Manutenção do Sistema

### 4.1 Atualização do NayBinho NAS

```bash
# Via CLI
sudo naybinho-update

# O comando executa:
# 1. Verifica versão atual e disponível
# 2. Baixa atualização
# 3. Faz backup das configurações
# 4. Aplica atualização
# 5. Reinicia serviços afetados
```

### 4.2 Atualização do Sistema Base (Ubuntu)

```bash
sudo apt update && sudo apt upgrade -y
sudo apt autoremove -y

# Para upgrades de kernel (requer reboot)
sudo apt full-upgrade -y
sudo reboot
```

### 4.3 Verificação de Saúde dos Discos

```bash
# SMART de todos os discos
for disk in /dev/sd?; do
    echo "=== $disk ===" 
    sudo smartctl -H $disk
done

# Teste curto SMART
sudo smartctl -t short /dev/sda

# Resultado após ~2 minutos
sudo smartctl -a /dev/sda | grep -A5 "Self-test execution"
```

### 4.4 Verificação do RAID (mdadm)

```bash
# Status de todos os arrays
cat /proc/mdstat

# Detalhes de um array específico
sudo mdadm --detail /dev/md0

# Verificar consistência (pode levar horas)
echo check | sudo tee /sys/block/md0/md/sync_action

# Monitorar progresso
watch -n 5 cat /proc/mdstat
```

### 4.5 Limpeza de Espaço

```bash
# Remover pacotes desnecessários
sudo apt autoremove -y
sudo apt autoclean

# Remover imagens Docker não utilizadas
docker system prune -a

# Limpar logs antigos
sudo journalctl --vacuum-time=30d

# Verificar maiores consumidores de espaço
sudo du -sh /* 2>/dev/null | sort -rh | head -20
```

---

## 5. Segurança

### 5.1 Hardening Básico

```bash
# Desabilitar login root via SSH
sudo sed -i 's/PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config

# Usar somente autenticação por chave
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart sshd

# Configurar fail2ban (já instalado)
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
sudo fail2ban-client status
```

### 5.2 Firewall (UFW)

```bash
# Status atual
sudo ufw status verbose

# Regras padrão do NayBinho NAS
sudo ufw allow 8080/tcp    # Interface Web
sudo ufw allow 8443/tcp    # Interface Web HTTPS
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 445/tcp     # SMB
sudo ufw allow 2049/tcp    # NFS
sudo ufw allow 111/tcp     # NFS Portmapper

# Bloquear IP específico
sudo ufw deny from 10.0.0.50

# Habilitar
sudo ufw enable
```

### 5.3 Auditoria de Acesso

```bash
# Ver logins recentes
last -n 20

# Tentativas de login falhas
sudo grep "Failed password" /var/log/auth.log | tail -20

# Usuários logados agora
who

# Processos dos usuários
ps aux --sort=-%cpu | head -10
```

### 5.4 Certificado SSL Let's Encrypt

```bash
# Instalar certbot (já disponível)
sudo certbot certonly --standalone \
  -d naybinho-nas.meudominio.com.br \
  --agree-tos -m admin@meudominio.com.br

# Configurar no NayBinho NAS
sudo /opt/naybinho/scripts/install-ssl.sh \
  /etc/letsencrypt/live/naybinho-nas.meudominio.com.br/fullchain.pem \
  /etc/letsencrypt/live/naybinho-nas.meudominio.com.br/privkey.pem
```

---

## 7. Ciclo de Atualização e Releases no GitHub

O NayBinho NAS possui um pipeline contínuo de build de ISOs e auto-atualização do sistema totalmente integrado ao GitHub Releases.

### 7.1 Como as Novas ISOs e Releases são Geradas

1. **Via GitHub Actions (`.github/workflows/build-and-release-iso.yml`)**:
   - Disparado automaticamente ao criar uma tag (ex: `git tag v1.0.1 && git push origin v1.0.1`) ou manualmente em *Actions → Run workflow*.
   - Compila os ativos do frontend React (`npm run build`).
   - Empacota o pacote de atualização `naybinho-update-vX.Y.Z.tar.gz`.
   - Gera a ISO bootável `naybinho-nas-vX.Y.Z-amd64.iso` baseada em Ubuntu 26.04.1 LTS via chroot e squashfs.
   - Gera checksums SHA256 e o manifesto `release.json`.
   - Publica os binários diretamente em **Releases** no GitHub.

2. **Via Script Local / Servidor (`build/create-release.sh`)**:
   ```bash
   chmod +x build/create-release.sh
   ./build/create-release.sh 1.0.1 "NayBinho NAS 1.0.1"
   ```

### 7.2 Detecção de Atualizações pelo Sistema Instalado

- O serviço `UpdateService` (`backend/services/update_service.py`) consulta periodicamente a API do GitHub (`/repos/naybinho/nas/releases/latest`).
- Se houver uma tag superior à versão atual:
  - Um alerta visual aparece no topo da interface web (*Header* e *Dashboard*).
  - O sistema exibe o link direto e tamanho da nova ISO (`.iso`) para quem deseja criar uma nova mídia USB.
  - O sistema exibe as notas de versão (Changelog) da release.

### 7.3 Auto-Atualização com 1 Clique (Zero Fricção)

Quando o administrador clica em **"Atualizar Sistema Automaticamente"**:
1. **Backup Automático**: Cria cópia de segurança do banco SQLite e configurações.
2. **Download do Pacote**: Baixa o pacote oficial de atualização `naybinho-update.tar.gz` da release do GitHub.
3. **Validação de Checksum**: Compara o hash SHA256 para garantir integridade.
4. **Aplicação dos Arquivos**: Atualiza o backend, o frontend compilado e scripts de sistema.
5. **Atualização de Pacotes do SO**: Executa `apt-get upgrade` de segurança do Ubuntu.
6. **Reinicialização Atômica**: Recarrega o systemd e reinicia os serviços `naybinho-backend`, `naybinho-frontend` e `naybinho-monitor`.
7. **Rollback de Segurança**: Em caso de falha de inicialização, reverte para o backup anterior.

---

## 8. Contatos e Suporte

### 6.1 Interface Web Não Acessível

```bash
# Verificar se o serviço está rodando
sudo systemctl status naybinho-api

# Reiniciar o serviço
sudo systemctl restart naybinho-api

# Ver logs de erro
sudo journalctl -u naybinho-api -n 100 --no-pager

# Verificar porta em uso
sudo ss -tlnp | grep 8080

# Testar localmente
curl -v http://localhost:8080/api/system/info
```

### 6.2 Compartilhamento SMB Não Funciona

```bash
# Verificar serviço Samba
sudo systemctl status smbd nmbd

# Testar configuração
sudo testparm

# Ver compartilhamentos ativos
sudo smbstatus

# Reiniciar Samba
sudo systemctl restart smbd nmbd

# Verificar usuário Samba
sudo pdbedit -L

# Redefinir senha Samba de um usuário
sudo smbpasswd admin
```

### 6.3 Compartilhamento NFS Não Funciona

```bash
# Verificar serviço NFS
sudo systemctl status nfs-server

# Ver exports ativos
sudo exportfs -v

# Atualizar exports após mudança
sudo exportfs -ra

# Reiniciar NFS
sudo systemctl restart nfs-server rpcbind

# Testar do cliente
showmount -e 192.168.1.100
```

### 6.4 Docker Não Inicia

```bash
# Status do Docker
sudo systemctl status docker

# Logs do Docker daemon
sudo journalctl -u docker -n 50

# Reiniciar Docker
sudo systemctl restart docker

# Verificar espaço em disco (causa comum)
df -h /var/lib/docker

# Limpar dados Docker
docker system prune -f
```

### 6.5 RAID Degradado

```bash
# Ver status
cat /proc/mdstat
sudo mdadm --detail /dev/md0

# Identificar disco falho (marcado como [F])
# Remover disco falho
sudo mdadm /dev/md0 --fail /dev/sdb1
sudo mdadm /dev/md0 --remove /dev/sdb1

# (Após substituir o disco fisicamente)
# Adicionar novo disco
sudo mdadm /dev/md0 --add /dev/sdb1

# Monitorar reconstrução
watch -n 10 cat /proc/mdstat
```

### 6.6 Sistema Sem Espaço em Disco

```bash
# Verificar uso
df -h
du -sh /var/* | sort -rh | head -20

# Limpar logs antigos
sudo journalctl --vacuum-size=500M
sudo find /var/log -name "*.gz" -delete

# Limpar cache APT
sudo apt clean

# Verificar arquivos grandes
sudo find / -size +1G -type f 2>/dev/null
```

### 6.7 Alta Temperatura

```bash
# Verificar temperatura da CPU
sensors

# Temperatura dos discos
sudo hddtemp /dev/sda /dev/sdb

# Via SMART
sudo smartctl -A /dev/sda | grep Temp

# Verificar velocidade dos fans
sensors | grep fan
```

---

## 7. Logs e Diagnóstico

### 7.1 Logs Principais

| Log | Localização | Conteúdo |
|---|---|---|
| Sistema | `journalctl` | Logs do systemd |
| NayBinho API | `journalctl -u naybinho-api` | Backend da interface |
| Samba | `/var/log/samba/` | Acesso SMB |
| NFS | `journalctl -u nfs-server` | Montagens NFS |
| Docker | `journalctl -u docker` | Docker daemon |
| Auth | `/var/log/auth.log` | Autenticação SSH/login |
| Kernel | `/var/log/kern.log` | Mensagens do kernel (disco/hardware) |
| SMART | Via `smartctl` | Saúde dos discos |

### 7.2 Comandos de Diagnóstico Úteis

```bash
# Resumo geral do sistema
neofetch
htop

# Uso de memória detalhado
free -h
vmstat -s

# I/O dos discos em tempo real
iostat -xz 2

# Conexões de rede ativas
ss -s
netstat -tuln

# Processos mais pesados
ps aux --sort=-%mem | head -10
ps aux --sort=-%cpu | head -10

# Informações de hardware
lshw -short
lspci
lsblk -a

# Erros de hardware recentes
sudo dmesg | grep -i error | tail -20
sudo dmesg | grep -i "hard disk" | tail -20
```

### 7.3 Relatório de Diagnóstico

Gere um relatório completo para suporte:

```bash
sudo /opt/naybinho/scripts/diagnostic-report.sh

# Arquivo gerado em /tmp/naybinho-diagnostic-YYYY-MM-DD.tar.gz
# Compartilhe este arquivo ao abrir uma issue no GitHub
```

---

## 8. Recuperação de Desastres

### 8.1 Cenários e Ações

| Cenário | Impacto | Ação |
|---|---|---|
| Falha 1 disco (RAID 1/5/10) | Degradado, dados OK | Substituir disco, aguardar reconstrução |
| Falha 2 discos (RAID 6) | Degradado, dados OK | Substituir discos urgente |
| Corrupção do OS (disco do sistema) | Interface inacessível | Reinstalar OS, restaurar config |
| Falha total de RAID | Perda de dados | Restaurar de backup externo |
| Esqueci a senha admin | Sem acesso à interface | Reset via console/SSH |

### 8.2 Resetar Senha do Administrador

**Via console local ou SSH:**

```bash
sudo /opt/naybinho/scripts/reset-admin-password.sh
# Digite e confirme a nova senha
```

**Via modo de recuperação:**

1. Reinicie o servidor
2. No menu GRUB, selecione **"Modo de Recuperação"**
3. Acesse o shell root
4. Execute: `naybinho-passwd admin`

### 8.3 Plano de Contingência Recomendado

```
✅ BACKUP 3-2-1:
   3 cópias dos dados
   2 mídias diferentes
   1 cópia offsite (nuvem ou local externo)

✅ DOCUMENTAÇÃO:
   Registre o IP, credenciais e configurações
   Guarde o backup de config em local seguro

✅ TESTES REGULARES:
   Teste a restauração trimestralmente
   Faça testes SMART mensais
   Verifique o RAID semanalmente
```

---

*Para perguntas, consulte o [FAQ.md](FAQ.md) ou abra uma issue no [GitHub](https://github.com/naybinho/naybinho-nas/issues).*
