# ❓ Perguntas Frequentes (FAQ) — NayBinho NAS

> Encontre respostas rápidas para as 35 dúvidas mais comuns sobre instalação, armazenamento, redes, docker e manutenção do NayBinho NAS.

---

## 📋 Sumário por Categorias

1. [Geral e Instalação (1–8)](#geral-e-instalação)
2. [Armazenamento e RAID (9–16)](#armazenamento-e-raid)
3. [Compartilhamentos e Rede (17–23)](#compartilhamentos-e-rede)
4. [Docker e Loja de Aplicativos (24–29)](#docker-e-loja-de-aplicativos)
5. [Segurança, Backup e Administração (30–35)](#segurança-backup-e-administração)

---

## Geral e Instalação

### 1. O que é o NayBinho NAS?
O NayBinho NAS é um sistema operacional completo para Home Labs e servidores de armazenamento doméstico e empresarial, construído sobre a base sólida do **Ubuntu 26.04.1 LTS**. Ele inclui uma interface web moderna, gerenciamento flexível de RAID/ZFS, loja integrada de containers Docker e compartilhamentos SMB/NFS.

### 2. O NayBinho NAS é gratuito e de código aberto?
Sim! O sistema é 100% gratuito e open source sob a licença **MIT**, sem limitações de capacidade, discos ou recursos pagos.

### 3. Posso instalar o NayBinho NAS em um PC antigo?
Sim. O requisito mínimo é um processador x86-64 de 2 núcleos, 4 GB de memória RAM e uma porta de rede Gigabit. Qualquer computador fabricado nos últimos 10–12 anos funciona perfeitamente.

### 4. Preciso de um disco dedicado apenas para o sistema operacional?
Sim, é altamente recomendado. O instalador prepara o disco do sistema com partição de boot, swap e root (`/`). Recomenda-se um SSD pequeno (32 GB a 128 GB) para o sistema operacional, deixando os demais discos exclusivamente para os pools de armazenamento de dados.

### 5. Posso instalar o NayBinho NAS em um pendrive ou cartão SD como faz o TrueNAS/Unraid?
Embora seja tecnicamente possível, **não recomendamos** pendrives USB comuns como disco do sistema operacional devido à alta quantidade de gravações de logs e banco de dados SQLite, o que causaria desgaste precoce da memória flash. Use um SSD SATA ou NVMe.

### 6. Como descubro o endereço IP do meu NAS após a instalação?
Ao término da instalação e após o primeiro boot, o console físico (monitor conectado ao NAS) exibe uma tela com os endereços IPv4 atribuídos pelo roteador (ex: `http://192.168.1.100:8080`) e o hostname mDNS `http://naybinho-nas.local:8080`.

### 7. Posso testar o NayBinho NAS em uma Máquina Virtual (VM)?
Com certeza. O NayBinho NAS pode ser virtualizado no **Proxmox VE**, **VMware ESXi / Workstation**, **Hyper-V** ou **VirtualBox**. Para testar o gerenciamento de discos e RAID, configure pelo menos 3 discos virtuais na VM.

### 8. Esqueci a senha de administrador da interface web. O que fazer?
Acesse o terminal do servidor fisicamente ou via SSH e execute o utilitário de recuperação:
```bash
sudo /opt/naybinho/scripts/reset-admin-password.sh
```
Você poderá definir uma nova senha para o usuário `admin` imediatamente.

---

## Armazenamento e RAID

### 9. Qual a diferença entre RAID 0, RAID 1, RAID 5, RAID 6 e RAID 10?
- **RAID 0:** Soma a capacidade e velocidade dos discos; **zero** tolerância a falhas (se 1 quebrar, perde tudo).
- **RAID 1:** Espelhamento idêntico entre 2 discos; tolera a quebra de 1 disco.
- **RAID 5:** Distribui dados e paridade entre 3 ou mais discos; tolera a quebra de 1 disco.
- **RAID 6:** Dupla paridade com 4 ou mais discos; tolera a quebra simultânea de até 2 discos.
- **RAID 10:** Combinação de espelhamento e striping (mínimo 4 discos); alta performance e tolerância a falhas.

### 10. Posso misturar discos de marcas, velocidades ou capacidades diferentes no mesmo RAID?
Sim, o `mdadm` permite a criação, mas o array será limitado pela capacidade do **menor disco** do conjunto. Por exemplo: discos de 2 TB, 4 TB e 4 TB em RAID 5 enxergarão cada disco como tendo apenas 2 TB. Recomenda-se usar discos de capacidades equivalentes.

### 11. O NayBinho NAS suporta ZFS?
Sim! O ZFS está nativamente compilado no kernel do Ubuntu 26.04 LTS. Você pode criar zpools diretamente pelo menu **Storage → Volumes**, com suporte a snapshots instantâneos, compressão lz4/zstd e scrub periódico.

### 12. O que acontece quando um disco do meu RAID falha?
O sistema envia uma notificação imediata (por email, Telegram, Discord, etc.), o dashboard aponta o status **Degradado (Degraded)** e indica exatamente o número de série e porta do disco com defeito. O NAS continua funcionando normalmente durante o período de tolerância.

### 13. Como faço para substituir um disco com defeito no RAID?
1. Acesse **Storage → RAID**, selecione o array e marque o disco falho como *Offline / Desanexar*.
2. Troque o disco fisicamente no servidor.
3. No painel, selecione o novo disco e clique em **Adicionar ao Array**. A sincronização (resync) iniciará automaticamente em segundo plano.

### 14. O que é o monitoramento SMART e por que ele é importante?
O SMART (Self-Monitoring, Analysis and Reporting Technology) monitora parâmetros vitais do disco rígido ou SSD, como temperatura, setores defeituosos realocados (`Reallocated_Sector_Ct`) e horas de uso. O NayBinho NAS avisa você antes que o disco falhe por completo.

### 15. Posso expandir a capacidade de um array RAID existente sem apagar os dados?
Sim. Em arrays RAID 5 e RAID 6, você pode adicionar um novo disco ao array já existente e clicar em **Expandir Volume (Grow)**. O sistema redistribui a paridade sem indisponibilidade dos dados.

### 16. O NayBinho NAS formata discos em quais sistemas de arquivos?
São suportados: **ext4** (padrão robusto do Linux), **XFS** (excelente para grandes massas de arquivos contínuos), **ZFS** e **Btrfs**.

---

## Compartilhamentos e Rede

### 17. Como configuro IP Estático no NayBinho NAS?
Vá em **Configurações → Rede → Interfaces**, edite a interface cabeada, alterne de DHCP para Estático, informe IP, Máscara, Gateway e DNS e clique em **Aplicar**. O sistema realiza um teste de conexão antes de tornar a alteração definitiva.

### 18. Consigo acessar meus arquivos pelo celular ou tablet?
Sim. Você pode utilizar qualquer aplicativo compatível com o protocolo SMB (como o app *Arquivos* nativo do iPhone/iPad ou o *CX File Explorer* no Android) conectando em `smb://<ip-do-nas>/nome-do-share`.

### 19. Qual a velocidade máxima de transferência que devo esperar em rede Gigabit (1 GbE)?
Uma rede 1 Gbps atinge teoricamente 125 MB/s. Na prática, transferências SMB de arquivos sequenciais (como filmes e imagens ISO) atingem entre **110 e 118 MB/s**.

### 20. O que é Link Aggregation (Bonding) e quando devo utilizá-lo?
O Bonding combina duas ou mais placas de rede físicas. Se você possui duas interfaces de 1 Gbps conectadas a um switch compatível com LACP (802.3ad), dois computadores podem baixar arquivos simultaneamente a 115 MB/s cada, totalizando ~230 MB/s de vazão total no servidor.

### 21. Meus arquivos apagados pela rede podem ser recuperados?
Sim, desde que a **Lixeira de Rede (Recycle Bin)** esteja ativada nas opções do compartilhamento SMB. Os arquivos excluídos são movidos para a pasta oculta `.recycle` dentro do próprio share.

### 22. O Windows acusa "Não é possível acessar o compartilhamento por política de convidado". Como resolver?
O Windows 10 e 11 recentes desabilitam acesso guest/anônimo por padrão. Para resolver:
- Crie um usuário no NayBinho NAS em **Usuários** e forneça credenciais válidas ao conectar;
- Ou habilite no Windows o acesso guest em `gpedit.msc` → *Modelos Administrativos* → *Rede* → *Estação de Trabalho Lanman* → *Habilitar logons de convidado não seguros*.

### 23. Como compartilho uma pasta exclusivamente para máquinas Linux de forma otimizada?
Crie um compartilhamento **NFS** em **Shares → NFS**, especificando o IP ou faixa de rede da sua máquina Linux com a opção `rw` e `sync`.

---

## Docker e Loja de Aplicativos

### 24. Preciso saber comandos do Docker no terminal para instalar apps?
Não. A **Loja de Aplicativos (App Store)** possui mais de 50 aplicativos populares (Plex, Jellyfin, Nextcloud, Home Assistant, Pi-hole, qBittorrent, etc.) prontos para instalação com apenas 1 clique através da interface visual.

### 25. Onde ficam salvos os dados e arquivos dos containers Docker?
Por padrão, os dados persistentes ficam armazenados no caminho `/mnt/dados/appdata/<nome-do-app>`. Dessa forma, mesmo que você atualize ou recrie o container, suas preferências e bancos de dados continuam intactos.

### 26. Posso usar aceleração de hardware (transcodificação por GPU Intel QuickSync / NVIDIA) no Plex ou Jellyfin?
Sim. O kernel do Ubuntu 26.04 já traz os drivers i915 integrados. Na instalação do Jellyfin/Plex pela loja de apps, marque a opção **Pass-through de GPU (QuickSync/NVIDIA)** para mapear `/dev/dri` diretamente no container.

### 27. Como atualizo um aplicativo instalado pela loja?
Vá em **Apps → Instalados**. Caso exista uma imagem mais recente no Docker Hub, um aviso com o botão **Atualizar** aparecerá. O NayBinho NAS faz o pull da nova imagem, reaplica os volumes e recria o container preservando suas configurações.

### 28. Posso fazer deploy de meus próprios arquivos `docker-compose.yml` customizados?
Sim. Na seção **Docker → Compose**, há um editor visual com syntax highlighting onde você pode colar ou carregar qualquer arquivo `docker-compose.yml` e clicar em **Deploy**.

### 29. Os containers Docker reiniciam sozinhos se o servidor reiniciar?
Sim, todos os containers criados pela loja ou pelo gerenciador vêm com a política `restart: unless-stopped` configurada por padrão.

---

## Segurança, Backup e Administração

### 30. Como faço backup das configurações do NayBinho NAS?
Vá em **Configurações → Backup → Criar Backup de Configurações**. O sistema gerará um arquivo `.tar.gz` contendo todos os usuários, compartilhamentos, agendamentos e regras de rede. Guarde este arquivo em outro computador ou pendrive.

### 31. O NayBinho NAS possui firewall integrado?
Sim, ele vem com o **UFW (Uncomplicated Firewall)** e o **Fail2ban** pré-instalados e integrados ao painel. Tentativas repetidas de força bruta via SSH ou login web bloqueiam o IP do atacante automaticamente.

### 32. Como configuro acesso externo seguro ao meu NAS pela internet?
Para acessar fora de casa com máxima segurança:
- **Recomendado:** Instale a extensão do **Tailscale** ou **WireGuard** pela Loja de Apps para criar uma VPN ponto-a-ponto sem necessidade de abrir portas no roteador;
- **Alternativa:** Configure um túnel **Cloudflare Tunnels** ou use um proxy reverso (Nginx Proxy Manager) com certificado SSL Let's Encrypt. Nunca exponha a porta 8080/SMB diretamente para a internet sem VPN.

### 33. O sistema suporta certificados SSL/HTTPS gratuitos?
Sim. Na aba **Configurações → SSL/TLS**, você pode gerar certificados válidos e com renovação automática via **Let's Encrypt** caso possua um domínio público apontado para seu IP.

### 34. Como recebo alertas em caso de aquecimento, disco com defeito ou falha de backup?
Acesse **Configurações → Notificações**. O sistema suporta notificações automáticas via **Telegram**, **Discord**, **Email (SMTP)**, **Slack** e **Pushover**. Basta preencher o webhook ou token correspondente e clicar em *Testar Notificação*.

### 35. Como desligo ou reinicio o NAS com total segurança para não corromper discos?
No canto superior direito da interface web, clique no botão de energia e selecione **Reiniciar** ou **Desligar**. O sistema desmontará todos os volumes, paralisará com segurança os containers Docker e sincronizará os buffers de disco antes de enviar o sinal ACPI de desligamento.
