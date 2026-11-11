# Contexto do projeto ADEC — Painel de CI/CD (FastAPI + React + GHCR)

> Documento para contextualizar uma LLM sobre este projeto. Estado registrado em **11/11/2026**.
> Leia inteiro antes de propor mudanças. As decisões listadas aqui já foram tomadas e
> testadas; não as reverta sem perguntar.

---

## 1. O trabalho (requisitos da faculdade)

Trabalho final da disciplina **Abordagem DevOps e Entregas Contínuas** (ADS, FAETERJ), feito em
grupo de 3 pessoas. A entrega é **só uma apresentação de 15 minutos em sala**, com demonstração
ao vivo a partir do repositório (não há relatório escrito).

**Combinação do grupo (única na turma):** Python (FastAPI) + React (Vite) + **GitHub Container Registry (GHCR)**.

**Integrantes (logins do GitHub):** `alv4roso4res` (Alvaro, dono do repo e do token do backend), `GustaReis-bit` (Gustavo) e `DrawnGZN`. Todos são colaboradores do repositório.

### Requisitos obrigatórios
- Repositório **público** no GitHub.
- Aplicação com etapa de build e **pelo menos 3 testes automatizados**.
- Workflow do GitHub Actions (`.github/workflows/*.yml`) com:
  - gatilho `pull_request` para a `main` → build + testes;
  - gatilho `push` na `main` (merge) → build + testes + **entrega**.
- **Branch `main` protegida**: merge só via PR e só com o pipeline aprovado.
- Só ferramentas gratuitas, sem cartão de crédito.

### Critérios de avaliação
| Critério | Peso |
|---|---|
| Pipeline de build e teste disparando no PR | 25% |
| Pipeline completo no merge na main, com a entrega funcionando | 25% |
| Branch protegida e merge bloqueado quando os testes falham | 15% |
| Explicação clara de o que fizeram, o que usaram e como fizeram | 20% |
| Participação de todos e respeito ao tempo de 15 min | 15% |

### Roteiro da apresentação (15 min)
1. **2 min — O que fizeram:** a aplicação e a combinação stack + plataforma.
2. **3 min — O que usaram:** linguagem/framework, testes, plataforma de entrega e motivos.
3. **5 min — Como fizeram:** workflow explicado (gatilhos, jobs, build/teste, condição da entrega, branch protegida).
4. **4 min — Ao vivo:** (1) abrir um PR e mostrar o pipeline na aba Actions; (2) mostrar um PR com teste falhando e o merge bloqueado; (3) fazer o merge e mostrar o pipeline até a entrega publicada.
5. **1 min — Dificuldades.**

### Regras
- Todos os integrantes falam.
- **Cada integrante precisa ter pelo menos um Pull Request próprio** no histórico.
- Demonstração ao vivo (vídeo/prints só como plano B se a internet falhar).

---

## 2. A ideia da aplicação

Um **painel de uma tela só (sem scroll)** que mostra o **pipeline do próprio repositório do
trabalho**, consultando a API do GitHub através da nossa API (FastAPI). A ideia é que o app
**faça parte da demonstração**: durante a apresentação, o painel mostra ao vivo o PR, o pipeline
rodando, o merge bloqueado, o deploy e a versão nova entrando no ar.

### Os 6 cards (já aprovados)
1. **Status da main** — último run do workflow na main: estado grande (sucesso/falha/rodando/fila), jobs `build-test` e `deploy` com as etapas, cronômetro.
2. **Últimos runs** — barrinhas dos ~20 últimos runs (altura = duração, cor = resultado, ícone PR/push) + taxa de sucesso, duração média, nº de deploys.
3. **PRs abertos** — autor, título, selo de estado (pronto / aguardando checks / testes falharam / precisa de aprovação / conflito…), botões **Aprovar** e **Mergear** (chamam a API do GitHub via nosso backend).
4. **Integrantes** — avatar, PRs abertos/mergeados, commits, ✓ se já tem ≥ 1 PR (regra do trabalho).
5. **Versão publicada vs. main** — versão rodando × última tag no GHCR × último commit da main → "atualizado", "aguardando reinício", "pipeline em andamento" etc. Também dispara o recarregamento automático da página.
6. **Commits da main** — últimos commits com SHA curto, mensagem, autor, tempo relativo e bolinha com o resultado do pipeline daquele commit.

### Momentos de demo planejados
- Um colega abre um PR (do notebook dele); o dono do token (Alvaro) **aprova e mergeia pelo app**.
- Clicar em **Mergear** num PR com teste falhando → o GitHub recusa (405) → o app mostra
  "bloqueado pela proteção da branch" (prova ao vivo da branch protegida).
- Um PR muda **a cor de fundo** da página; após o merge, o deploy automático atualiza o
  container e a página **troca de cor sozinha** (recarrega ao detectar versão nova).

### Restrições importantes da demo
- **Ninguém aprova o próprio PR** no GitHub. Como o token do backend é do Alvaro, o botão
  "Aprovar" só funciona em PRs de outros integrantes.
- A proteção da main precisa ter **"Do not allow bypassing the above settings"** ligado; senão o
  token de admin consegue mergear mesmo com teste falhando.

---

## 3. Arquitetura

```
  CÓDIGO (GitHub)          PIPELINE (GitHub Actions)          PRODUÇÃO (notebook do Alvaro)
 ┌───────────────┐        ┌─────────────────────────┐        ┌──────────────────────┐
 │ api/          │  PR ──►│ build-test              │        │ watch-deploy.sh      │
 │ frontend/     │        │                         │        │   pull a cada 20s    │
 │ ci.yml        │ merge─►│ build-test ─► deploy ───┼─► GHCR ┼─► docker compose     │
 └───────────────┘        └─────────────────────────┘        │   ├─ frontend (nginx)│
                                                             │   └─ api (FastAPI)   │
                                                             └──────────────────────┘
```

- **Duas imagens** no GHCR: `ghcr.io/alv4roso4res/adec-api` e `ghcr.io/alv4roso4res/adec-frontend` (nomes sempre minúsculos). Pacotes públicos.
- **Frontend**: React compilado servido por **nginx**, que também faz proxy de `/api/*` para o container da API (mesma origem, sem CORS).
- **API**: FastAPI/uvicorn, sem porta exposta ao host; só o nginx fala com ela pela rede interna do Docker.
- **docker-compose.yml** na raiz orquestra os dois (frontend em `localhost:8080`, publicado só em `127.0.0.1`).
- **Produção = notebook do Alvaro** rodando `scripts/watch-deploy.sh`, que a cada 20s faz
  `docker compose pull && docker compose up -d` da tag `latest` (o GHCR só guarda imagens, não executa nada).
- **Versão** (`APP_VERSION`) = SHA curto (7 chars) do commit, embutido nas duas imagens no build.
  Aparece em `GET /api/health` e em `/version.json` (servido pelo nginx, sem cache).

### Estratégia de tags
| Tag | Quem cria | Para quê |
|---|---|---|
| `sha-<7 chars>` | job `deploy` (build + push) | imutável; identifica o commit; rollback |
| `latest` | passo "Promover latest" do `deploy` (`docker buildx imagetools create`) | ponteiro móvel; é o que a produção observa |

A `latest` só é movida **depois** que as duas imagens `sha-` foram publicadas, para a produção
nunca receber API nova + frontend velho. Rollback: `IMAGE_TAG=sha-xxxxxxx` no `.env` da raiz.

---

## 4. Estrutura atual do repositório

Repositório: **`github.com/alv4roso4res/adec`** (público). Remote via SSH.

```
ADEC_trabalho/
├── .github/workflows/ci.yml     # pipeline (build-test + deploy) — na main desde o PR #1
├── .env.example / .env          # GHCR_OWNER=alv4roso4res, IMAGE_TAG=latest, APP_VERSION=dev (.env fora do git)
├── .gitignore                   # .env, .idea/, node_modules/, dist/, __pycache__/, .venv/
├── README.md                    # explica o CI/CD e aponta para este roadmap
├── contexto_projeto_adec.md     # ESTE arquivo
├── docker-compose.yml
├── scripts/
│   ├── watch-deploy.sh          # vigia de produção (WATCH_INTERVAL, padrão 20s)
│   └── check-local.sh           # roda localmente o que o build-test roda (--docker p/ imagens)
├── api/
│   ├── Dockerfile               # multi-stage, uv 0.13.6, python:3.13-slim, usuário não-root, HEALTHCHECK via urllib
│   ├── .env.example / .env      # .env fora do git
│   ├── pyproject.toml / uv.lock # deps: fastapi[standard], pydantic-settings; dev: pytest, pytest-asyncio, respx
│   ├── src/api/
│   │   ├── main.py              # create_app(settings); OPENAPI_TAGS; lifespan cria httpx.AsyncClient + GitHubClient
│   │   ├── config.py            # Settings (ver §7 "Configuração")
│   │   ├── deps.py              # get_settings, get_http_client, get_github_client (de app.state), require_write_actions
│   │   ├── errors.py            # GitHubError + handler; GITHUB_ERROR_RESPONSES / WRITE_ERROR_RESPONSES (OpenAPI)
│   │   ├── github/cache.py      # ResponseCache: TTL + ETag + lock por chave (single-flight)
│   │   ├── github/client.py     # GitHubClient: leitura com TTLs por recurso; approve_pull/merge_pull sem cache + invalidate_pulls()
│   │   ├── schemas/             # common (ApiModel, RunStatus, ErrorResponse), health, pipeline, commits, version, team, pulls
│   │   ├── services/            # pipeline, commits, version, team, pulls (funções puras)
│   │   └── routes/              # health, pipeline (fetch_history_runs compartilhada), commits, version, team, pulls
│   └── tests/
│       ├── conftest.py          # Settings de teste (_env_file=None), app, client, github_fixture
│       ├── fixtures/github/     # JSON reais reduzidos: runs, jobs, commits, pacotes, PRs, checks, reviews, contribuidores
│       ├── github/              # test_cache, test_client (respx)
│       ├── services/            # um test_<card>.py por service
│       ├── routes/              # fakes.py (FakeGitHubClient), um test_<rota>.py por rota (+ test_pulls_write)
│       ├── schemas/test_common.py
│       ├── test_config.py, test_errors.py
│       └── test_openapi.py      # trava a convenção de documentação (§10)
└── frontend/
    ├── Dockerfile               # node:22-alpine → nginx:1.31.8-alpine
    ├── nginx.conf               # SPA + proxy /api/ + no-store em index.html e version.json
    ├── vite.config.ts           # proxy /api → :8000 (sem rewrite); plugin que gera dist/version.json
    ├── .env.example             # VITE_API_URL=/api
    └── src/
        ├── App.tsx              # só <ParticlesBackground/> + <main class="app"/>
        ├── index.css            # --color-background (fundo da tela toda) e --color-particle-1..4
        ├── components/ParticlesBackground.tsx   # tsparticles v4; fundo lido de --color-background (PR #6)
        ├── services/api.ts      # request<T>() + ApiError; endpoints de exemplo (A/B/C) a substituir
        └── types/api.ts         # tipos de exemplo a substituir
```

### Rotas implementadas (todas documentadas em `/api/docs`)
| Rota | Card | Etapa |
|---|---|---|
| `GET /api/health` | cabeçalho (versão, repositório, escrita ligada) | base / R9 |
| `GET /api/pipeline/current` | 1 | R4 |
| `GET /api/pipeline/history?limit=` | 2 | R4 |
| `GET /api/commits?limit=` | 6 | R5 |
| `GET /api/version` | 5 | R6 |
| `GET /api/team` | 4 | R7 |
| `GET /api/pulls` | 3 | R8 |
| `POST /api/pulls/{number}/approve` | 3 (Aprovar) | R9 |
| `POST /api/pulls/{number}/merge` | 3 (Merge) | R9 |

**`errors.py` — `GitHubError(status_code, message, rate_limited=False)` → status nosso:**
| GitHub | Nossa resposta |
|---|---|
| 401 / 403 (auth) | 502 |
| 403 com rate limit / 429 | 503 |
| 405 (merge não permitido) | 409 |
| ≥ 500, timeout ou erro de rede | 502 |
| outros | o mesmo status |

Resposta de erro: `{"detail": "<mensagem>"}`.

---

## 5. Pipeline (`.github/workflows/ci.yml`)

Segue o esqueleto do professor (mesmos gatilhos e nomes de jobs `build-test` e `deploy`).
Steps têm nomes em português (serão mostrados na apresentação).

- `permissions: contents: read` no topo; `packages: write` **só** no job `deploy`.
- `concurrency`: PRs cancelam runs antigos do mesmo PR; pushes na main entram em fila (não cancelam).

**`build-test`** (PR e push):
1. checkout
2. `setup-uv` (cache) → `uv sync --locked` → `uv run pytest -v` (em `api/`)
3. `setup-node` 22 (cache npm) → `npm ci` → `npm run lint` → `npm run build` (em `frontend/`)
4. `docker build` das duas imagens **sem push**, com cache `type=gha` (scope por imagem) — valida Dockerfiles e aquece o cache do deploy

**`deploy`** (`needs: build-test`, `if: github.event_name == 'push'`):
1. `SHORT_SHA=${GITHUB_SHA::7}`, `OWNER` em minúsculas
2. login no `ghcr.io` com `GITHUB_TOKEN`
3. build + push `adec-api:sha-$SHORT_SHA` e `adec-frontend:sha-$SHORT_SHA` (`APP_VERSION=$SHORT_SHA`)
4. promove `latest` das duas com `docker buildx imagetools create`
5. resumo em `$GITHUB_STEP_SUMMARY`

Versões de actions usadas: `checkout@v7`, `setup-uv@v10.3.3`, `setup-node@v7`,
`setup-buildx-action@v4`, `login-action@v4`, `build-push-action@v7`. Se alguma não existir,
o run falha cedo com "Unable to resolve action" — basta ajustar a versão.

---

## 6. Status

### ✅ Feito
- Ideia do app e os 6 cards definidos.
- Dockerfiles, nginx, docker-compose; publicação no GHCR (tags `sha-` + promoção da `latest`); pacotes públicos com acesso Write para o Actions.
- Produção local com `watch-deploy.sh` testada (troca de versão ao vivo comprovada).
- **Pipeline no ar (R1):** PR #1 → `build-test` verde no PR; merge → `deploy` verde. Todos os merges desde então passaram (runs de ~2 min).
- **Branch `main` protegida (R2, classic rule):** PR obrigatório com 1 aprovação; check obrigatório `build-test`; "up to date" desligado; **"Do not allow bypassing" ligado**; force push e deleção bloqueados. Consequência: nem o dono mergeia sem aprovação de outro integrante.
- Colaboradores: `GustaReis-bit` (ativo; já aprovou e mergeou PRs) e `DrawnGZN` (convidado).
- **Backend completo (R3–R9):** os seis cards, aprovar/mergear PR pelo app e documentação OpenAPI obrigatória. R3–R8 na main; R9 commitada e a caminho do PR.
- **Metade da R11:** fundo da tela vindo de `--color-background` (PR #6, do Gustavo).

### Histórico de PRs
| PR | Autor | Conteúdo | Etapa |
|---|---|---|---|
| #1 | alv4roso4res | `ci.yml` + README do CI/CD | R1 |
| #2 | alv4roso4res | Settings novas + `ApiModel` camelCase | R3a |
| #3 | alv4roso4res | Este roadmap + `scripts/check-local.sh` | docs |
| #4 / #5 | alv4roso4res | `GitHubClient` de leitura / cache TTL + ETag (o #5 entrou junto com o #4) | R3b/R3c |
| #6 | GustaReis-bit | Fundo lido de `--color-background` | R11 (parte) |
| #7 | alv4roso4res | Rotas de pipeline (cards 1 e 2) | R4 |
| #8 | alv4roso4res | Documentação OpenAPI completa + `test_openapi.py` | docs |
| #9 | alv4roso4res | Rota de commits (card 6) | R5 |
| #10 | alv4roso4res | Rota de versão (card 5) | R6 |
| #11 | alv4roso4res | Rota de integrantes (card 4) | R7 |
| #12 | alv4roso4res | Rota de PRs abertos com badges (card 3, leitura) | R8 |
| #13 | alv4roso4res | READMEs de execução local/produção; contexto duplicado corrigido | docs |

### Roadmap de execução

Cada etapa de código vira um PR pequeno; distribuir a autoria entre os três integrantes.

| Etapa | Entrega | Depende de | Situação |
|---|---|---|---|
| R0 — Validar a base | Roadmap e `scripts/check-local.sh` | — | ✅ 03/11 |
| R1 — Publicar o pipeline | PR do `ci.yml`, `build-test` no PR e `deploy` no merge | R0 | ✅ PR #1 |
| R2 — Governança e demo de falha | Proteção da main, colaboradores e PR propositalmente quebrado | R1 | 🟡 Proteção e colaboradores ✅ · **falta o PR com teste quebrado** (guardar a branch, sem mergear) |
| R3 — Base do backend | Configuração, `ApiModel`, cache TTL/ETag e client de leitura | R2 | ✅ PRs #2, #4, #5 |
| R4 — Pipeline | Cards 1 e 2 | R3 | ✅ PR #7 |
| R5 — Commits | Card 6, cruzamento com runs em cache | R4 | ✅ PR #9 |
| R6 — Versão | Card 5, duas imagens, comparação de SHAs por prefixo | R4, R5 | ✅ PR #10 |
| R7 — Equipe | Card 4 com todos os logins configurados | R3 | ✅ PR #11 |
| R8 — PRs: leitura | Card 3, checks, reviews, badges e permissões | R3 | ✅ PR #12 |
| R9 — PRs: escrita | Aprovar/mergear, bloqueio por configuração, invalidação de cache | R8 | ✅ branch `feat/backend-pulls-write` |
| R10 — Painel | Grade dos seis cards, contratos reais, polling, carregamento/erro | R4–R9 | ⬜ |
| R11 — Atualização visual | Recarregamento por `version.json`, reconexão e fundo vindo do CSS | R10 | 🟡 Fundo ✅ (PR #6) · falta recarregamento/reconexão |
| R12 — Ensaio | Roteiro dividido, PRs de demo e plano B | R11 | ⬜ |

### Pendências que não são código
- **DrawnGZN sem PR próprio** (regra do trabalho). Confirmar que aceitou o convite; a R9 ou um PR do frontend (R10/R11) pode ser dele.
- **PR com teste quebrado** para a demo do merge bloqueado (vale 15%).
- No dia: **vigia rodando** antes de entrar na sala (`nohup ./scripts/watch-deploy.sh > watch-deploy.log 2>&1 &`) e `curl localhost:8080/api/health` mostrando o SHA do último merge.

**Risco conhecido:** a promoção das duas `latest` é sequencial, sem transação entre imagens; o vigia pode pegar uma atualização parcial. Na demo, conferir que API e frontend estão no mesmo SHA; se não, repetir a promoção do mesmo SHA.

---

## 7. Plano do backend (implementado)

### Princípio
```
rota  →  GitHubClient (busca + cache + erros)  →  service (função PURA)  →  schema (resposta)
```
- **Services nunca fazem requisição**: recebem os `dict` crus do GitHub e devolvem schemas.
  Testes carregam JSON de fixture e conferem a saída — sem rede, sem token (o CI não tem o token).
- **JSON de saída em camelCase** via `ApiModel` base com `alias_generator=to_camel` (Python continua snake_case).
- **Datas em ISO UTC**; o frontend formata "há X min".
- **Uma rota por card** (ritmos de atualização diferentes; um card quebrado não derruba os outros).

### Estrutura alvo
```
api/src/api/
├── github/cache.py      # cache com TTL + ETag
├── github/client.py     # um método por recurso do GitHub
├── schemas/common.py    # ApiModel (camelCase) + enums de status
├── schemas/{pipeline,pulls,team,version,commits}.py
├── services/{pipeline,pulls,team,version,commits}.py
└── routes/{health,pipeline,pulls,team,version,commits}.py
api/tests/
├── fixtures/github/     # JSON reais salvos com `gh api ...`
├── github/test_client.py
├── services/test_*.py
└── routes/test_*.py
```

### Limite de requisições — cache com ETag (essencial)
O card 3 faz ~1 + 3 chamadas por PR; com polling a cada 10s estouraria 5.000 req/h.
Solução: guardar o `ETag` de cada resposta e mandar `If-None-Match`; **respostas 304 não contam
no rate limit**. TTLs: runs/jobs 5s · PRs/checks/reviews 10s · commits 15s · pacotes 30s ·
contribuidores/PRs totais 60s. Chamadas por PR em paralelo (`asyncio.gather`). Invalidar cache
de PRs após aprovar/mergear. Detectar rate limit por `x-ratelimit-remaining: 0`.

### Métodos do GitHubClient
| Método | Endpoint |
|---|---|
| `list_workflow_runs(branch, event, limit)` | `GET /repos/{o}/{r}/actions/workflows/{arquivo}/runs` |
| `list_run_jobs(run_id)` | `GET /actions/runs/{id}/jobs` |
| `list_pulls(state, limit)` | `GET /pulls` |
| `get_pull(n)` | `GET /pulls/{n}` (`mergeable_state`) |
| `list_check_runs(sha)` | `GET /commits/{sha}/check-runs` |
| `list_reviews(n)` | `GET /pulls/{n}/reviews` |
| `list_commits(branch, limit)` | `GET /commits?sha=main` |
| `list_contributors()` | `GET /contributors` |
| `list_package_versions(image)` | `GET /users/{owner}/packages/container/{image}/versions` |
| `get_authenticated_user()` | `GET /user` (cache longo) |
| `approve_pull(n)` | `POST /pulls/{n}/reviews` `{"event":"APPROVE"}` |
| `merge_pull(n, method)` | `PUT /pulls/{n}/merge` |

### Rotas e contratos (camelCase)
- `GET /api/pipeline/current` → `{ run: {id, status, event, branch, headSha, commitMessage, actor, startedAt, durationSeconds, htmlUrl} | null, jobs: [{name, status, durationSeconds, steps:[{name, status, number}]}] }`
  - `status` ∈ `queued | in_progress | success | failure | cancelled` (normaliza `status`+`conclusion` do GitHub).
  - `run: null` quando ainda não há runs.
- `GET /api/pipeline/history?limit=20` → `{ runs: [{id, status, event, branch, headSha, durationSeconds, createdAt}], stats: {total, successRate, avgDurationSeconds, deploys, byEvent} }`
  - média só de runs concluídos; taxa de sucesso ignora cancelados; duração = `updated_at − run_started_at` (em andamento: até agora).
- `GET /api/pulls` → `[{number, title, author:{login, avatarUrl}, createdAt, htmlUrl, headSha, checks:{passed, failed, pending}, approvals, badge, canApprove, canMerge}]`
  - `badge` (ordem de prioridade): `draft` → `conflict` (dirty) → `checks_failed` → `waiting_checks` (pendente ou sem checks) → `computing` (`mergeable_state` unknown) → `needs_approval` (blocked + checks verdes) → `ready` (clean).
  - `canApprove` = escrita ligada E autor ≠ dono do token E ainda não aprovado por ele.
  - `canMerge` = escrita ligada (fica habilitado mesmo bloqueado, de propósito, para mostrar a recusa na demo).
- `POST /api/pulls/{n}/approve` e `POST /api/pulls/{n}/merge` → `{ok, message}`
  - dependência `require_write_actions` → 403 se `ENABLE_WRITE_ACTIONS=false`.
  - erros: 422 do GitHub (aprovar o próprio PR) → 422; 405 no merge → 409; 409 do GitHub → 409.
- `GET /api/health` → `{status, version, repository, writeActionsEnabled}` — `repository` = `GITHUB_OWNER/GITHUB_REPO`; usado no cabeçalho do painel e no healthcheck da imagem.
- `GET /api/team` → `[{login, avatarUrl, prsOpen, prsMerged, commits, meetsRequirement}]` — sempre lista todos de `TEAM_LOGINS`, mesmo com 0 PRs.
- `GET /api/version` → `{ running, mainSha, images:[{name, publishedSha}], state }`
  - `publishedSha` = tag `sha-xxxx` que está na mesma versão de pacote que a `latest`.
  - `state` ∈ `up_to_date | restart_pending | building | pipeline_failed | dev`.
  - **Comparar SHAs por prefixo** (Actions usa 7 chars; `git rev-parse --short` pode usar mais).
- `GET /api/commits?limit=8` → `[{sha, shortSha, message (1ª linha), author:{login, avatarUrl}, committedAt, htmlUrl, pipelineStatus}]` — `pipelineStatus` cruzado com os runs já em cache (sem chamada extra).

### Configuração (`api/.env`) — implementada na R3a
| Variável | Padrão | Observação |
|---|---|---|
| `GITHUB_TOKEN` | `""` | classic com `public_repo` + `read:packages`; vazio = anônimo |
| `GITHUB_OWNER` / `GITHUB_REPO` | `""` | repositório monitorado |
| `GITHUB_WORKFLOW_FILE` | `ci.yml` | workflow dos cards 1 e 2 |
| `TEAM_LOGINS` | `[]` | `a,b,c` ou JSON |
| `GHCR_IMAGES` | `adec-api,adec-frontend` | `a,b` ou JSON |
| `GHCR_OWNER` | = `GITHUB_OWNER` | sempre minúsculo |
| `APP_VERSION` | `dev` | no Docker vem do build-arg; não definir no `.env` |
| `ENABLE_WRITE_ACTIONS` | `false` | libera aprovar/mergear |
| `MERGE_METHOD` | `merge` | `merge` ou `squash` |
| `PULLS_LIMIT` / `HISTORY_LIMIT` | 5 / 20 | `ge=1` |

Saíram `GHCR_PACKAGE` e `CACHE_TTL_SECONDS` (os TTLs agora são fixos por recurso no client) e a dependência `cachetools`.

**Token do backend (`api/.env`)**: classic com `public_repo` + `read:packages`. **Não** é o token
de publicar imagens (`write:packages`), nem o `GITHUB_TOKEN` do Actions.

Antes de existirem runs, os cards 1/2 ficam vazios: tratar vazio e, em dev, pode-se apontar
`GITHUB_OWNER/REPO/WORKFLOW_FILE` para outro repositório público com Actions.

### Decisões tomadas na implementação (R3–R5)
- **Cache próprio** (`ResponseCache`) em vez do `cachetools.TTLCache`: a entrada expirada é mantida para reaproveitar o ETag (`If-None-Match` → 304 não gasta rate limit). Lock por chave = *single-flight* (duas requisições iguais simultâneas viram uma).
- Client: parâmetros `None` não entram na query nem na chave; erros não são cacheados; timeout/erro de rede → 502; corpo de erro sem JSON → "Erro N do GitHub".
- TTLs: runs/jobs 5 s · PRs/checks/reviews 10 s · commits 15 s · pacotes 30 s · contribuidores 60 s · `/user` 3600 s.
- **O cache devolve o mesmo objeto**: services nunca alteram o que recebem (há teste para isso).
- `RunStatus` ganhou **`skipped`** (job `deploy` quando o `build-test` falha). Normalização: queued/waiting/requested/pending → queued; in_progress; completed + success/cancelled; skipped/neutral → skipped; qualquer outra conclusão → failure.
- **Deploy** (card 2) = run de `push` na `main` com status success (o run só fica verde se o deploy passar).
- Card 1 usa `list_workflow_runs(branch="main", event="push", limit=1)`.
- `fetch_history_runs()` (routes/pipeline.py) é a chamada única de runs dos cards 2 e 6: mesmos argumentos = mesma chave de cache.
- Commits: `author` tem `name` além de `login`/`avatarUrl` (login nulo quando o e-mail não está ligado a uma conta); `pipelineStatus` = run mais recente do SHA, preferindo `push`, senão `pull_request`, senão null.

### Detalhes já definidos para R7–R9
- **Equipe:** logins comparados sem diferenciar maiúsculas; ordem = `TEAM_LOGINS`; integrante sem atividade aparece com zeros e avatar `https://github.com/<login>.png`; `meetsRequirement` = pelo menos 1 PR de autoria (aberto, mergeado ou fechado); `commits` vem de `/contributors` (commits na branch padrão de contas vinculadas).
- **PRs (leitura):** checks contados com o filtro padrão `latest` do GitHub; `skipped`/`neutral` não contam; `approvals` = revisores cujo último review (ignorando COMMENTED) é APPROVED; `mergeable_state` clean/unstable/has_hooks → `ready`, blocked → `needs_approval`, unknown/null/outros → `computing`; sem token ou com escrita desligada, não chama `/user` e `canApprove` = false; `canApprove` também é false em draft.
- **PRs (escrita):** chamadas sem cache; sucesso invalida o cache de PRs; mensagens do GitHub preservadas em `detail`; o compose publica a porta só em `127.0.0.1` (na rede da faculdade, ninguém mais aprova/mergeia com o token do Alvaro).

### Ordem de implementação (1 fase = 1 PR)
1. Base: `ApiModel`, cache ETag, métodos de leitura do client, testes do client.
2. Cards 1 e 2 (pipeline atual + histórico).
3. Card 6 (commits).
4. Card 5 (versão) — depende de 2 e 3.
5. Card 4 (equipe).
6. Card 3 leitura (PRs + badges).
7. Card 3 escrita (aprovar/mergear + `require_write_actions`).

### Testes previstos
pipeline (normalização de status, duração em andamento, stats com cancelados, lista vazia) ·
pulls (um caso por badge, `canApprove` falso no próprio PR, `canMerge` com escrita desligada) ·
team (integrante sem PR, login fora do time ignorado) · version (um caso por estado) ·
commits (1ª linha da mensagem, cruzamento com runs) · client (304 reaproveita cache, rate limit → 503,
invalidação após merge) · rotas (200 + formato; 403 nas rotas de escrita).

---

## 8. Plano do frontend (R10–R11)

- Layout em grade 3 colunas × 2 linhas, `height: 100vh`, cada card com `overflow: hidden` e limite de itens. **Testar em 1366×768** (projetor).
  ```
  │ 1. Status da main │ 3. PRs abertos (Aprovar/Merge) │ 5. Versão      │
  │ 2. Últimos runs   │ 6. Commits da main             │ 4. Integrantes │
  ```
  Cabeçalho com nome do repo, indicador "ao vivo" e versão.
- Polling por card (card 1: 5s se rodando, 30s parado; demais 10–60s).
- **Recarregamento automático**: consultar `/version.json` a cada ~10s; se a versão mudar em relação à carregada, `location.reload()`. Durante a troca de container mostrar "reconectando…" em vez de erro.
- **Fundo trocável por PR** ✅ (PR #6): o `ParticlesBackground` e o `body` leem `--color-background`; o PR de demo muda **uma linha** do `index.css` e a tela inteira troca de cor (após o recarregamento automático).
- Substituir os endpoints/tipos de exemplo em `services/api.ts` e `types/api.ts` pelos contratos da §7.

---

## 9. Credenciais (nunca commitar)
| Credencial | Onde fica | Uso |
|---|---|---|
| chave SSH | `~/.ssh` | `git push` |
| token classic `write:packages` | `~/.docker/config.json` (docker login) | publicação manual no GHCR (o CI não usa) |
| `GITHUB_TOKEN` | gerado por run do Actions | deploy do pipeline |
| token classic `public_repo` + `read:packages` | `api/.env` | backend ler/aprovar/mergear |

---

## 10. Convenções e cuidados para quem for mexer no código
- Todas as rotas da API ficam sob **`/api`** (o nginx e o proxy do Vite repassam sem reescrever).
- Services puros e testáveis; nada de rede em service.
- Testes não podem depender do `.env` local (`Settings(_env_file=None, ...)`).
- Nunca commitar `.env`, `.venv`, `node_modules`, `.idea`.
- Na máquina de "produção", **não rodar `docker compose build`** (criaria uma `latest` local e o teste do vigia deixaria de ser fiel). Imagens novas só vêm do GHCR.
- Os nomes de imagem/owner no GHCR são minúsculos.
- Manter os nomes dos jobs `build-test` e `deploy` (o check obrigatório da proteção se chama `build-test`).
- Mensagens/nomes de steps e textos da UI em português.
- **Documentação OpenAPI obrigatória** (Swagger em `/api/docs`): toda rota nova tem `summary`, `description`, `operation_id` e as respostas de erro (`responses=GITHUB_ERROR_RESPONSES` se fala com o GitHub; `WRITE_ERROR_RESPONSES` nas de escrita); todo campo tem `Field(description, examples)` e todo modelo tem docstring; o `tests/test_openapi.py` reprova o que faltar. Tags novas entram em `OPENAPI_TAGS` (`main.py`).

## 11. Comandos úteis
```bash
# Dev — API
cd api && uv sync && uv run pytest && uv run uvicorn api.main:app --reload   # :8000/api/docs
# Dev — frontend
cd frontend && npm ci && npm run dev                                          # :5173

# Produção local (imagens do GHCR)
docker compose pull && docker compose up -d && docker compose ps
./scripts/watch-deploy.sh
curl localhost:8080/api/health ; curl localhost:8080/version.json

# Inspecionar a latest no GHCR
docker buildx imagetools inspect ghcr.io/alv4roso4res/adec-frontend:latest
```

---

## 12. Dificuldades encontradas (para o minuto final da apresentação)
- **Commit local que não subiu:** arquivos commitados só na `ci/pipeline` local "sumiram" ao trocar para a `main`. Recuperados com `git checkout ci/pipeline -- <arquivos>`. Lição: conferir `git status`/`git log origin/...` antes de abrir PR.
- **Branch protegida sem bypass:** nem o dono do repo consegue mergear sem aprovação — o time passou a revisar os PRs uns dos outros.
- **Vigia de produção parado:** o terminal fechou e a produção ficou um deploy atrás. Solução: `nohup` + log e checar `/api/health` antes da demo.
- **PRs empilhados:** a R3c dependia da R3b ainda não publicada; resolvido mergeando na ordem com merge commit (não squash).
- **Rate limit do GitHub:** com polling, ~4 chamadas por PR estourariam 5.000 req/h; resolvido com cache TTL + ETag (304 não conta) e single-flight.

