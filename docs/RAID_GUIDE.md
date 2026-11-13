# 🛡️ NayBinho NAS — Guia Completo de RAID & Armazenamento

Bem-vindo ao guia de arquitetura e operação de arrays **RAID (Redundant Array of Independent Disks)** do **NayBinho NAS**. Este documento detalha os níveis suportados, requisitos de hardware, tolerância a falhas, procedimentos de reconstrução (*rebuild*) e recomendações para servidores Home Lab.

---

## 📊 Tabela Comparativa de Níveis RAID

| Nível RAID | Nome / Tipo | Mínimo de Discos | Tolerância a Falhas | Capacidade Útil (com $N$ discos de tamanho $S$) | Eficiência de Armazenamento | Desempenho Leitura | Desempenho Escrita |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **RAID 0** | Striping puro | 2 | **0 discos** *(Sem tolerância)* | $N \times S$ | 100% | ⚡ Muito Alto | ⚡ Muito Alto |
| **RAID 1** | Mirroring (Espelho) | 2 | **1 disco** *(ou $N-1$ em mirrors múltiplos)* | $1 \times S$ | $1/N$ (50% p/ 2 discos) | 🚀 Alto | ⚖️ Normal |
| **RAID 5** | Paridade Distribuída | 3 | **1 disco** | $(N - 1) \times S$ | $\frac{N-1}{N}$ (ex: 67% p/ 3 discos, 75% p/ 4 discos) | 🚀 Muito Alto | 📉 Moderado (cálculo de paridade) |
| **RAID 6** | Dupla Paridade Distribuída | 4 | **2 discos** simultâneos | $(N - 2) \times S$ | $\frac{N-2}{N}$ (ex: 50% p/ 4 discos, 67% p/ 6 discos) | 🚀 Muito Alto | 📉 Moderado |
| **RAID 10** | Stripe de Espelhos (1+0) | 4 *(número par)* | **1 por par espelhado** (até $N/2$ discos) | $(N / 2) \times S$ | 50% | ⚡ Extremo | 🚀 Alto |

---

## 🔍 Detalhamento por Nível de RAID

### 1. RAID 0 (Striping)
* **Como funciona:** Os dados são divididos em blocos (*chunks*, tipicamente 512KB) e distribuídos sequencialmente entre os discos participantes sem qualquer informação de paridade ou redundância.
* **Tolerância a falhas:** **Zero (0)**.
  > ⚠️ Se qualquer um dos discos apresentar defeito físico ou corrupção crítica, **todo o array é perdido irremediavelmente**.
* **Capacidade:** Se você possui 2 discos de 4TB, sua capacidade útil é **8TB**.
* **Quando usar:**
  - Caches temporários, scratch disks, renderização de vídeo descartável, pastas de downloads efêmeros.
  - **Nunca** utilize para armazenar backups, dados pessoais ou bancos de dados!

---

### 2. RAID 1 (Mirroring)
* **Como funciona:** Os mesmos dados são gravados identicamente em dois ou mais discos.
* **Tolerância a falhas:** **1 disco** (em um par espelhado).
  > 💡 Se você possui 2 discos de 4TB e um deles falha, o sistema continua funcionando perfeitamente a partir do disco sobrevivente sem perda de dados.
* **Capacidade:** 2 discos de 4TB resultam em **4TB** de capacidade útil.
* **Quando usar:**
  - Instalação do sistema operacional raiz (`/`), bancos de dados transacionais leves, diretórios de configuração do Docker.

---

### 3. RAID 5 (Paridade Simples Distribuída)
* **Como funciona:** Os blocos de dados e as informações de paridade (XOR) são alternados entre todos os discos do array.
* **Tolerância a falhas:** **1 disco**.
  > 🛡️ **Exemplo prático:** Se você tem 4 discos de 4TB em RAID 5 (16TB bruto):
  > - Capacidade útil: $(4 - 1) \times 4\text{TB} = \mathbf{12\text{TB}}$.
  > - Você pode perder qualquer 1 dos 4 discos e o array continuará operando em modo **Degradado** (*degraded*).
* **Quando usar:**
  - Excelente custo-benefício para servidores de mídia (Plex, Jellyfin), armazenamento central de documentos e fotos de família.
  - Recomendado com até 4 a 5 discos de tamanhos moderados (até 6TB). Para discos maiores (8TB+), prefira RAID 6 ou RAID 10 devido ao risco de falha secundária durante o rebuild (URE).

---

### 4. RAID 6 (Dupla Paridade Distribuída)
* **Como funciona:** Utiliza dois esquemas de paridade matematicamente independentes (P+Q Reed-Solomon), distribuídos por todas as unidades.
* **Tolerância a falhas:** **2 discos simultâneos**.
  > 🛡️ **Exemplo prático:** Se você tem 6 discos de 8TB em RAID 6:
  > - Capacidade útil: $(6 - 2) \times 8\text{TB} = \mathbf{32\text{TB}}$.
  > - Se o disco B falhar e, durante a troca, o disco D também falhar, **seus dados continuam intactos**!
* **Quando usar:**
  - Armazenamentos de grande volume (arrays com 6 ou mais discos grandes de 10TB+).
  - Ambientes de Home Lab que não possuem monitoramento presencial diário e exigem resiliência máxima.

---

### 5. RAID 10 (1+0 - Mirror + Stripe)
* **Como funciona:** Primeiro os discos são combinados em pares espelhados (RAID 1), e em seguida esses pares formam um conjunto striping (RAID 0).
* **Tolerância a falhas:** **1 disco por sub-espelho**. No melhor cenário, pode tolerar a falha de até metade de todos os discos ($N/2$), desde que não pertençam ao mesmo par espelhado.
  > 🛡️ **Exemplo prático:** Com 4 discos (A, B, C, D) onde A+B é um par e C+D é outro:
  > - Se A e C falharem simultaneamente, o array **continua operando 100%**.
  > - Capacidade útil: $(4 / 2) \times 4\text{TB} = \mathbf{8\text{TB}}$.
* **Quando usar:**
  - Cargas de trabalho intensivas de I/O aleatório: bancos de dados (PostgreSQL, MariaDB), volumes de máquinas virtuais (Proxmox/KVM) e containers de alta demanda.
  - Reconstrução (*rebuild*) mais rápida e com menor estresse mecânico de leitura se comparado ao RAID 5/6.

---

## 🔄 Procedimento de Recuperação e Rebuild

Quando o NayBinho NAS detectar uma falha através de `/proc/mdstat` ou alertas de SMART, siga este roteiro de manutenção:

### 1. Identificar o disco defeituoso
No dashboard do NayBinho NAS ou via CLI:
```bash
cat /proc/mdstat
mdadm --detail /dev/md0
```
Localize o disco com a flag `(F)` (*faulty*) ou ausente no mapa `[U_]`. Exemplo: `/dev/sdc`.

### 2. Se houver Hot Spare configurado
Se você adicionou um disco de **Hot Spare** anteriormente pelo NayBinho NAS, a sincronização se iniciará de forma **automática e imediata**! Você verá:
```text
md0 : active raid5 sde[3] sdd[2] sdc[4](F) sdb[0]
      ... [>....................]  recovery = 2.4% (speed=112000K/sec)
```

### 3. Substituição manual de disco defeituoso
Se não houver hot spare, substitua fisicamente o disco danificado e execute:

1. **Remover o disco com falha do array:**
   ```bash
   mdadm /dev/md0 --fail /dev/sdc --remove /dev/sdc
   ```
2. **Desconectar fisicamente e inserir o novo disco** (exemplo: reconhecido como `/dev/sdc` ou `/dev/sde`).
3. **Adicionar o novo disco ao array:**
   ```bash
   mdadm /dev/md0 --add /dev/sdc
   ```
4. **Acompanhar o progresso do Rebuild:**
   - O painel do NayBinho NAS atualizará o progresso e o tempo estimado em tempo real.
   - Pela linha de comando:
     ```bash
     watch -n 2 cat /proc/mdstat
     ```

---

## 🏆 Melhores Práticas para Home Labs

1. **A regra 3-2-1:**
   > 🚨 **RAID NÃO É BACKUP!** RAID garante **alta disponibilidade** e continuidade de serviço contra falha mecânica de hardware. Ele não protege contra exclusão acidental, ransomware, corrupção lógica de sistema de arquivos ou surtos elétricos. Sempre mantenha cópias de segurança externas!
2. **Monitoramento SMART Ativo:** Mantenha os testes curtos agendados semanalmente e testes longos mensais pelo painel de controle. Fique atento a:
   - `5 Reallocated_Sector_Ct > 0`
   - `197 Current_Pending_Sector > 0`
   - `187 Reported_Uncorrect > 0`
3. **Evite lotes idênticos no mesmo array:** Se comprar 4 discos de uma vez da mesma fábrica e lote, eles têm alta probabilidade de ter desgastes e defeitos simultâneos. Se possível, mescle fornecedores ou lotes.
4. **Use No-Break (UPS):** Quedas de energia abruptas durante operações de escrita podem causar o temido *write hole* em RAID 5 tradicional ou corromper superblocos. O NayBinho NAS suporta integração com `apcupsd` e `nut`.
5. **Utilize Hot Spare quando possível:** Em arrays remotos ou que ficam semanas sem manutenção física, configure um disco extra como sobressalente a quente (*Hot Spare*).
