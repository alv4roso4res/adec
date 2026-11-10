# Contexto do projeto ADEC — Painel de CI/CD (FastAPI + React + GHCR)

> Documento para contextualizar uma LLM sobre este projeto. Estado registrado em **03/11/2026**.
> Leia inteiro antes de propor mudanças. As decisões listadas aqui já foram tomadas e
> testadas; não as reverta sem perguntar.

---

## 1. O trabalho (requisitos da faculdade)

Trabalho final da disciplina **Abordagem DevOps e Entregas Contínuas** (ADS, FAETERJ), feito em
grupo de 3 pessoas. A entrega é **só uma apresentação de 15 minutos em sala**, com demonstração
ao vivo a partir do repositório (não há relatório escrito).

**Combinação do grupo (única na turma):** Python (FastAPI) + React (Vite) + **GitHub Container Registry (GHCR)**.

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
- **docker-compose.yml** na raiz orquestra os dois (frontend em `localhost:8080`).
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
├── .github/workflows/ci.yml     # pipeline (só na branch ci/pipeline, ainda não enviada)
├── .env.example / .env          # GHCR_OWNER=alv4roso4res, IMAGE_TAG=latest, APP_VERSION=dev (.env fora do git)
├── .gitignore                   # .env, .idea/, node_modules/, dist/, __pycache__/, .venv/
├── README.md                    # explica o CI/CD (na branch ci/pipeline)
├── docker-compose.yml
├── scripts/watch-deploy.sh      # vigia de produção (WATCH_INTERVAL, padrão 20s)
├── api/
│   ├── Dockerfile               # multi-stage, uv 0.13.6, python:3.13-slim, usuário não-root, HEALTHCHECK via urllib
│   ├── .dockerignore
│   ├── .env.example / .env      # .env fora do git
│   ├── pyproject.toml / uv.lock # deps: fastapi[standard], pydantic-settings, cachetools; dev: pytest, pytest-asyncio, respx
│   ├── src/api/
│   │   ├── main.py              # create_app(settings) + app = create_app(); lifespan cria 1 httpx.AsyncClient
│   │   ├── config.py            # Settings (pydantic-settings)
│   │   ├── deps.py              # get_settings, get_http_client (de app.state)
│   │   ├── errors.py            # GitHubError + handler (mapeamento de status)
│   │   ├── github/client.py     # GitHubClient — só a casca
│   │   ├── routes/health.py     # GET /api/health
│   │   ├── schemas/             # vazio
│   │   └── services/            # vazio
│   └── tests/
│       ├── conftest.py          # Settings de teste (_env_file=None), app, TestClient
│       ├── test_config.py
│       ├── test_errors.py
│       ├── routes/test_health.py
│       ├── services/.gitkeep
│       └── fixtures/.gitkeep
└── frontend/
    ├── Dockerfile               # node:22-alpine → nginx:1.31.8-alpine
    ├── nginx.conf               # SPA + proxy /api/ + no-store em index.html e version.json
    ├── vite.config.ts           # proxy /api → :8000 (sem rewrite); plugin que gera dist/version.json
    ├── .env.example             # VITE_API_URL=/api
    └── src/
        ├── App.tsx              # só <ParticlesBackground/> + <main class="app"/>
        ├── index.css            # variáveis --color-background e --color-particle-1..4
        ├── components/ParticlesBackground.tsx   # tsparticles v4 (fundo #0b0f1a FIXO no componente)
        ├── services/api.ts      # request<T>() + ApiError; endpoints de exemplo (A/B/C) a substituir
        └── types/api.ts         # tipos de exemplo a substituir
```

### Detalhes da API já existente

**`config.py` — variáveis (lidas do `api/.env`):**
| Variável | Padrão | Observação |
|---|---|---|
| `GITHUB_TOKEN` | `""` | sem token = chamadas anônimas |
| `GITHUB_OWNER` / `GITHUB_REPO` | `""` | repositório monitorado |
| `TEAM_LOGINS` | `[]` | aceita `a,b,c` ou JSON |
| `GHCR_PACKAGE` | `""` | **será substituída** por `GHCR_IMAGES` (ver §7) |
| `APP_VERSION` | `"dev"` | no Docker vem do build-arg |
| `ENABLE_WRITE_ACTIONS` | `false` | libera aprovar/mergear |
| `CACHE_TTL_SECONDS` | `15` | |

**`main.py`:** `create_app()` registra routers com `prefix="/api"`, docs em `/api/docs`,
`openapi` em `/api/openapi.json`; o `lifespan` cria o `httpx.AsyncClient` com
`base_url=https://api.github.com`, `Accept: application/vnd.github+json`,
`X-GitHub-Api-Version: 2022-11-28` e `Authorization: Bearer` (só se houver token).

**`errors.py` — `GitHubError(status_code, message, rate_limited=False)` → status nosso:**
| GitHub | Nossa resposta |
|---|---|
| 401 / 403 (auth) | 502 |
| 403 com rate limit / 429 | 503 |
| 405 (merge não permitido) | 409 |
| ≥ 500 | 502 |
| outros | o mesmo status |

Resposta de erro: `{"detail": "<mensagem>"}`.

**Testes atuais:** health (status, versão, rotas antigas removidas, lifespan cria/fecha o client),
config (padrões, parsing de `TEAM_LOGINS`), errors (mapeamento parametrizado + handler).

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
- Bootstrap da API (config, create_app, lifespan, erros, health) com testes passando.
- Frontend base (Vite + React + partículas), proxy do Vite, geração de `version.json`.
- Dockerfiles (API e frontend), nginx, docker-compose, `.dockerignore`, `.gitignore`.
- Publicação manual no GHCR testada (tags `sha-` + promoção da `latest` com `imagetools`).
- Pacotes `adec-api` e `adec-frontend` **públicos** e com **acesso Write para o Actions** do repositório `adec`.
- Produção local com `watch-deploy.sh` testada: troca de versão ao vivo comprovada.
- `buildx` instalado na máquina do Alvaro (`docker-buildx`, Ubuntu).
- Repositório `alv4roso4res/adec` criado; `main` enviada (inclui `api/`; um `api/.git` aninhado foi removido).
- Workflow `ci.yml` + README criados na branch **`ci/pipeline`** (1 commit); branch enviada para `origin` em 03/11/2026. PR ainda pendente.

### Roadmap de execução

Atualizado após inspeção local em **03/11/2026**. Cada fase de código deve virar
um PR pequeno; distribuir a autoria entre os três integrantes. A ordem abaixo
preserva os contratos e as decisões das seções 7 e 8.

| Etapa | Entrega | Depende de | Critério de conclusão |
|---|---|---|---|
| R0 — Validar a base | Roadmap e `scripts/check-local.sh` | — | Testes da API, lint e build do frontend aprovados; builds Docker conferidos |
| R1 — Publicar o pipeline | Enviar `ci/pipeline`, abrir PR e acompanhar Actions | R0 | `build-test` verde no PR; merge seguido de `deploy` verde, imagens publicadas e produção com o mesmo SHA |
| R2 — Governança e demo de falha | Proteção da main, colaboradores e PR propositalmente quebrado | R1 | 1 aprovação e `build-test` obrigatórios, sem bypass; merge do PR vermelho recusado; branch preservada |
| R3 — Base do backend | Configuração prevista na §7, `ApiModel`, cache TTL/ETag e client de leitura | R2 | Testes sem rede para cache, 304, expiração, erros e rate limit; camelCase e configuração cobertos |
| R4 — Pipeline | Cards 1 e 2: schemas, services puros e rotas | R3 | Status, duração, estatísticas, cancelados e ausência de runs cobertos por testes |
| R5 — Commits | Card 6 e cruzamento com runs em cache | R4 | Primeira linha da mensagem, autor e status corretos, sem chamada extra para runs |
| R6 — Versão | Card 5, duas imagens e comparação de SHAs por prefixo | R4, R5 | Testes dos cinco estados e de versões divergentes entre API/frontend |
| R7 — Equipe | Card 4 com todos os logins configurados | R3 | Integrante sem atividade aparece; pessoas externas não entram na contagem do time |
| R8 — PRs: leitura | Card 3, checks, reviews, badges e permissões | R3 | Um teste por badge, incluindo PR próprio, draft e checks ausentes |
| R9 — PRs: escrita | Aprovar/mergear, bloqueio por configuração e invalidação de cache | R8 | Escrita desligada retorna 403; erros do GitHub preservados/mapeados; cache invalidado após sucesso |
| R10 — Painel | Grade dos seis cards, contratos reais, polling e estados de carregamento/erro | R4–R9 | Tela utilizável em 1366×768, falha de um card isolada e ações de PR funcionais |
| R11 — Atualização visual | Recarregamento por `version.json`, reconexão e fundo vindo do CSS | R10 | PR de uma linha muda a cor após entrega; recarregamento automático observado |
| R12 — Ensaio | Roteiro dividido, PRs de demo e plano B | R11 | Três integrantes com PR próprio; ensaio em 15 minutos e demonstrações de sucesso, bloqueio e atualização |

**R0 concluída em 03/11/2026:** `bash scripts/check-local.sh --docker` terminou
com sucesso: 17 testes da API, instalação pelos lockfiles, lint, build do frontend,
sintaxe dos scripts e builds Docker das duas imagens (`check-local`). Parte dos
builds reutilizou cache local; o runner do Actions ainda precisa validar o workflow.
O npm reportou 12 vulnerabilidades moderadas, a revisar em um PR de dependências
sem aplicar atualizações forçadas durante a preparação da demonstração.

**R1 iniciada:** `git push -u origin ci/pipeline` concluído. Próxima ação: abrir
o PR em https://github.com/alv4roso4res/adec/pull/new/ci/pipeline e acompanhar
`build-test`. O envio contém o commit de pipeline preexistente; o roadmap, o script
de validação e a atualização do README permanecem como alterações locais sem commit.

**Atenção para R1:** promover duas tags `latest` é uma operação sequencial, sem
transação entre imagens. O vigia pode observar uma atualização parcial se consultar
o registro entre as promoções ou se a segunda falhar. Confirmar a igualdade das
versões das duas imagens na demonstração; caso isso ocorra, repetir a promoção do
mesmo SHA antes de continuar. A estratégia atual permanece, mas não garante
atomicidade entre os dois pacotes.

#### Checklist operacional de R1 e R2

1. `git push -u origin ci/pipeline` e abrir o PR → ver o `build-test` rodar.
2. Fazer o merge → ver o `deploy` publicar e o vigia atualizar a produção sozinho.
3. **Proteger a `main`** (classic rule): PR obrigatório com **1 aprovação**; status check
   obrigatório **`build-test`**; "require branches up to date" **desligado**;
   **"Do not allow bypassing the above settings" ligado**.
4. Convidar os 2 colegas como **colaboradores** (Settings → Collaborators) — necessário para criarem branches e para a aprovação deles contar.
5. Criar um PR com teste quebrado de propósito, confirmar o merge bloqueado e **guardar a branch** (sem mergear) para a apresentação.

### 🔜 Depois
- Backend completo (plano na §7), em fases, cada fase = 1 PR (dividir entre os integrantes).
- Frontend dos 6 cards (plano na §8).
- Alguns testes com Vitest no frontend (opcional, mas bom).
- Ensaiar a apresentação e preparar os PRs de demonstração.

---

## 7. Plano do backend (aprovado, ainda não implementado)

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
- `GET /api/team` → `[{login, avatarUrl, prsOpen, prsMerged, commits, meetsRequirement}]` — sempre lista todos de `TEAM_LOGINS`, mesmo com 0 PRs.
- `GET /api/version` → `{ running, mainSha, images:[{name, publishedSha}], state }`
  - `publishedSha` = tag `sha-xxxx` que está na mesma versão de pacote que a `latest`.
  - `state` ∈ `up_to_date | restart_pending | building | pipeline_failed | dev`.
  - **Comparar SHAs por prefixo** (Actions usa 7 chars; `git rev-parse --short` pode usar mais).
- `GET /api/commits?limit=8` → `[{sha, shortSha, message (1ª linha), author:{login, avatarUrl}, committedAt, htmlUrl, pipelineStatus}]` — `pipelineStatus` cruzado com os runs já em cache (sem chamada extra).

### Mudanças de configuração previstas
| Variável | Mudança |
|---|---|
| `GHCR_PACKAGE` | sai → **`GHCR_IMAGES=adec-api,adec-frontend`** |
| `GHCR_OWNER` | nova (padrão = `GITHUB_OWNER`) |
| `GITHUB_WORKFLOW_FILE` | nova (padrão `ci.yml`) |
| `MERGE_METHOD` | nova (`merge` ou `squash`, padrão `merge`) |
| `PULLS_LIMIT` / `HISTORY_LIMIT` | novas (5 / 20) |

**Token do backend (`api/.env`)**: classic com `public_repo` + `read:packages`. **Não** é o token
de publicar imagens (`write:packages`), nem o `GITHUB_TOKEN` do Actions.

Antes de existirem runs, os cards 1/2 ficam vazios: tratar vazio e, em dev, pode-se apontar
`GITHUB_OWNER/REPO/WORKFLOW_FILE` para outro repositório público com Actions.

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

## 8. Plano do frontend (ainda não implementado)

- Layout em grade 3 colunas × 2 linhas, `height: 100vh`, cada card com `overflow: hidden` e limite de itens. **Testar em 1366×768** (projetor).
  ```
  │ 1. Status da main │ 3. PRs abertos (Aprovar/Merge) │ 5. Versão      │
  │ 2. Últimos runs   │ 6. Commits da main             │ 4. Integrantes │
  ```
  Cabeçalho com nome do repo, indicador "ao vivo" e versão.
- Polling por card (card 1: 5s se rodando, 30s parado; demais 10–60s).
- **Recarregamento automático**: consultar `/version.json` a cada ~10s; se a versão mudar em relação à carregada, `location.reload()`. Durante a troca de container mostrar "reconectando…" em vez de erro.
- **Fundo trocável por PR**: hoje o `ParticlesBackground` tem `#0b0f1a` fixo e o canvas cobre o `body`. Ajustar para ler `--color-background` do CSS, para que o PR de demo mude **uma linha** do `index.css` e a tela inteira troque de cor.
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
