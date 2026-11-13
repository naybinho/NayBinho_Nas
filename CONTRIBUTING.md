# 🤝 Guia de Contribuição — NayBinho NAS

Ficamos muito felizes pelo seu interesse em contribuir com o **NayBinho NAS**! Este é um projeto de código aberto mantido pela comunidade para tornar a experiência de montar e gerenciar um Home Lab simples, moderna e poderosa.

---

## Código de Conduta

Ao participar deste projeto, você concorda em manter um ambiente acolhedor, inclusivo e livre de assédio para todas as pessoas, independentemente de seu nível de experiência, identidade ou origem.

---

## Como Posso Contribuir?

Você pode ajudar o projeto de diversas formas:
1. **Reportando Bugs:** Encontrou um problema? Abra uma issue com detalhes para que possamos reproduzir e corrigir.
2. **Sugerindo Novas Funcionalidades:** Tem uma ideia incrível de recurso ou novo app para a loja? Compartilhe conosco!
3. **Melhorando a Documentação:** Correções ortográficas, traduções ou novos tutoriais são sempre bem-vindos.
4. **Enviando Código (Pull Requests):** Correções de bugs, novos recursos no frontend/backend ou melhorias nos scripts de build da ISO.

---

## Fluxo de Trabalho de Desenvolvimento

### 1. Preparação do Ambiente

#### Pré-requisitos
- **Git** instalado
- **Node.js 20+** e **npm** ou **pnpm** (para o Frontend)
- **Python 3.12+** e **virtualenv** (para o Backend)
- **Docker** (para testar containers e build da ISO)

#### Clonando o Repositório
```bash
git clone https://github.com/naybinho/naybinho-nas.git
cd naybinho-nas
```

#### Rodando o Backend em Desenvolvimento
```bash
cd backend
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate no Windows
pip install -r requirements.txt
uvicorn main:app --reload --port 8080
```

#### Rodando o Frontend em Desenvolvimento
```bash
cd frontend
npm install
npm run dev
```
Acesse `http://localhost:5173` no seu navegador. O frontend está configurado com proxy para redirecionar chamadas de API para a porta `8080`.

---

## Padrões de Commit e Branches

Utilizamos o padrão **Conventional Commits**:

- `feat: adiciona suporte a quotas de disco no samba`
- `fix: corrige cálculo de temperatura dos discos nvme`
- `docs: atualiza guia de instalação com requisitos de rede`
- `refactor: otimiza leitura de status do mdstat`
- `test: adiciona testes unitários para router de shares`
- `chore: atualiza dependências do backend`

### Estrutura de Branches
- `main`: Código estável pronto para produção e releases.
- `develop`: Branch de integração para novas funcionalidades.
- Branches de trabalho devem partir da `develop`:
  - `feature/nome-da-funcionalidade`
  - `fix/descricao-do-bug`

---

## Enviando um Pull Request (PR)

1. Faça um Fork do repositório.
2. Crie sua branch a partir da `develop`:
   ```bash
   git checkout -b feature/minha-melhoria
   ```
3. Faça suas alterações e garanta que os testes continuam passando.
4. Realize o commit seguindo os padrões convencionais.
5. Envie para o seu fork:
   ```bash
   git push origin feature/minha-melhoria
   ```
6. Abra um **Pull Request** apontando para a branch `develop` do repositório principal, preenchendo o template descritivo com o que foi feito.

---

## Dúvidas e Suporte

- Caso queira discutir uma ideia antes de implementar, abra uma discussão na aba **Discussions** do GitHub ou participe do nosso canal comunitário no Discord.
- Muito obrigado por fazer parte do NayBinho NAS! 🚀
