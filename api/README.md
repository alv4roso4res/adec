# ADEC — API + Frontend

Painel de uma tela que mostra o pipeline do próprio repositório, consultando a
API do GitHub **através da nossa API**. Este README cobre a base do projeto
(API, frontend e Docker); as chamadas ao GitHub e os cards vêm depois.

```
.
├── api/                  FastAPI (Python 3.13, uv, layout src/)
├── frontend/             React 19 + Vite + TypeScript
├── scripts/watch-deploy.sh
├── docker-compose.yml
└── .env.example          GHCR_OWNER, IMAGE_TAG, APP_VERSION
```

## Estrutura da API

```
api/
├── src/api/
│   ├── main.py           create_app(settings=None) + app = create_app()
│   ├── config.py         Settings (pydantic-settings) + get_settings() com lru_cache
│   ├── deps.py           get_settings / get_http_client / get_github_client (leem de request.app.state)
│   ├── errors.py         GitHubError + handler -> {"detail": ...} + GITHUB_/WRITE_ERROR_RESPONSES (OpenAPI)
│   ├── github/cache.py   ResponseCache: TTL + ETag (a entrada expirada guarda o ETag) e lock por chave
│   ├── github/client.py  GitHubClient: métodos de leitura do GitHub com cache, 304 e erros
│   ├── routes/health.py  GET /api/health (HealthResponse)
│   ├── routes/pipeline.py GET /api/pipeline/current e /api/pipeline/history (cards 1 e 2)
│   ├── routes/commits.py GET /api/commits (card 6)
│   ├── routes/version.py GET /api/version (card 5)
│   ├── routes/team.py    GET /api/team (card 4)
│   ├── routes/pulls.py   GET /api/pulls (card 3, leitura)
│   ├── services/pipeline.py funções puras: status normalizado, duração, stats
│   ├── services/commits.py função pura: commits × runs (status do pipeline por SHA)
│   ├── services/version.py função pura: running × latest no GHCR × main → state
│   ├── services/team.py  função pura: TEAM_LOGINS × PRs × contribuidores
│   ├── services/pulls.py função pura: PRs × detalhes × checks × reviews → badge, canApprove
│   ├── schemas/common.py ApiModel (JSON em camelCase) + RunStatus
│   ├── schemas/health.py HealthResponse
│   ├── schemas/pipeline.py respostas dos cards 1 e 2
│   ├── schemas/commits.py resposta do card 6
│   ├── schemas/version.py resposta do card 5 + VersionState
│   ├── schemas/team.py   resposta do card 4
│   └── schemas/pulls.py  resposta do card 3 + PullBadge
├── tests/                conftest.py, github/, routes/, schemas/, services/, fixtures/
├── Dockerfile
└── .env.example
```

- Tudo da API responde sob **`/api`** (inclusive `/api/docs` e `/api/openapi.json`).
- O `lifespan` cria **um** `httpx.AsyncClient` (base `https://api.github.com`,
  `Accept: application/vnd.github+json`, `X-GitHub-Api-Version`) em
  `app.state.http_client` e o fecha no shutdown. O header `Authorization:
  Bearer` só é enviado quando `GITHUB_TOKEN` não está vazio.
- No mesmo `lifespan` nasce o `GitHubClient` (com um `ResponseCache` próprio) em
  `app.state.github_client`; as rotas o recebem por `Depends(get_github_client)`.
  O client devolve os dicts crus do GitHub; quem transforma são os services.
- Cache do client: TTLs fixos por recurso (runs/jobs 5s · PRs/checks/reviews 10s ·
  commits 15s · pacotes 30s · contribuidores 60s · `/user` 1h). Depois do TTL a
  requisição vai com `If-None-Match`; um **304 não gasta rate limit** e só renova a
  validade. Chamadas iguais simultâneas viram uma requisição só (lock por chave).
  Rate limit é detectado por `x-ratelimit-remaining: 0`; timeout/falha de rede → 502.
- Mapeamento de erros do GitHub (`GitHubError`): 401/403 de autenticação → **502**,
  rate limit (429, ou 403 com `rate_limited=True`) → **503**, 405 no merge → **409**,
  demais 5xx → 502, outros 4xx mantêm o status.

### Documentação interativa (Swagger)

A documentação completa (rotas, parâmetros, schemas com exemplos e erros) fica em
**`/api/docs`**; o spec cru em `/api/openapi.json`.

- dev: <http://localhost:8000/api/docs>
- produção (Docker, via nginx): <http://localhost:8080/api/docs>

Toda rota nova precisa de `summary`, `description`, `operation_id` e das respostas
de erro (`responses=GITHUB_ERROR_RESPONSES` se fala com o GitHub); todo campo de
schema precisa de `Field(description=..., examples=[...])` e todo modelo de
docstring. O `tests/test_openapi.py` reprova o que faltar e diz qual rota/campo.

### Rotas

| Rota | Card | Resposta (camelCase) |
|---|---|---|
| `GET /api/health` | — | `{status, version}` |
| `GET /api/pipeline/current` | 1. Status da main | `{run: {id, status, event, branch, headSha, commitMessage, actor, startedAt, durationSeconds, htmlUrl} \| null, jobs: [{name, status, durationSeconds, steps: [{name, status, number}]}]}` |
| `GET /api/pipeline/history?limit=` | 2. Últimos runs | `{runs: [{id, status, event, branch, headSha, durationSeconds, createdAt}], stats: {total, successRate, avgDurationSeconds, deploys, byEvent}}` |
| `GET /api/commits?limit=` | 6. Commits da main | `[{sha, shortSha, message, author: {login, name, avatarUrl}, committedAt, htmlUrl, pipelineStatus}]` |
| `GET /api/version` | 5. Versão publicada vs. main | `{running, mainSha, images: [{name, publishedSha}], state}` |
| `GET /api/team` | 4. Integrantes | `[{login, avatarUrl, prsOpen, prsMerged, commits, meetsRequirement}]` |
| `GET /api/pulls` | 3. PRs abertos | `[{number, title, author: {login, avatarUrl}, createdAt, htmlUrl, headSha, checks: {passed, failed, pending}, approvals, badge, canApprove, canMerge}]` |

- Fluxo: rota → `GitHubClient` → service **puro** (recebe os dicts crus e um `now`
  em UTC; não faz requisição, não lê o relógio, não altera a entrada) → schema.
- `current`: último run do workflow em **push na `main`** e os jobs dele; `run: null`
  e `jobs: []` quando ainda não há runs.
- `history`: últimos runs de todos os eventos e branches. `limit` de 1 a 100
  (padrão `HISTORY_LIMIT`); fora disso → 422.
- `status` ∈ `queued | in_progress | success | failure | cancelled | skipped`
  (`status` + `conclusion` do GitHub; `skipped` aparece no job `deploy` quando o
  `build-test` falha; conclusões desconhecidas contam como `failure`).
- `durationSeconds`: do início até o fim quando concluído, até agora quando em
  andamento, `null` na fila. `startedAt`/`createdAt` em ISO UTC.
- Stats: `successRate` = sucessos / (sucessos + falhas), de 0 a 1 em 3 casas
  (cancelados, skipped e não concluídos ficam fora; `null` sem nenhum);
  `avgDurationSeconds` só de runs concluídos; `deploys` = push na `main` com
  sucesso; `byEvent` = contagem por evento.
- `commits`: últimos commits da `main` (`limit` de 1 a 30, padrão 8). `message` é
  só a 1ª linha; `shortSha` tem 7 caracteres; `author.login`/`avatarUrl` ficam
  `null` quando o e-mail do commit não está ligado a uma conta do GitHub.
  `pipelineStatus` = status do run mais recente (maior `created_at`) daquele SHA,
  preferindo `push` a `pull_request`; `null` se o SHA não está nos runs recentes.
  Os runs vêm da **mesma chamada** do card 2 (`fetch_history_runs`, sem `limit`),
  então caem na mesma chave do cache: o cruzamento não gasta requisição extra.
- `version`: `running` = `APP_VERSION`; `mainSha` = último commit da `main`;
  `publishedSha` de cada imagem de `GHCR_IMAGES` = a tag `sha-xxxxxxx` que está na
  mesma versão de pacote que a `latest` (`null` se não há `latest` ou o pacote ainda
  não existe — 404 não derruba o card). SHAs são comparados **por prefixo** (mínimo 7
  caracteres). `state`, avaliado nesta ordem:

  | `state` | Quando |
  |---|---|
  | `dev` | `APP_VERSION` não é um SHA (ex.: `dev`, fora do Docker) |
  | `up_to_date` | a `latest` de **todas** as imagens e a versão rodando são a main |
  | `restart_pending` | a `latest` de todas as imagens já é a main, mas a produção roda outra versão |
  | `pipeline_failed` | a `latest` não é a main e o último run de **push** da main falhou/foi cancelado |
  | `building` | qualquer outro caso: run da main na fila/rodando/ainda não criado, ou concluído com o GHCR ainda mostrando a `latest` anterior, ou imagens divergentes no meio da promoção |

  Imagens com `latest` divergente (API movida, frontend não) nunca contam como
  publicadas. Commits e runs vêm das **mesmas chamadas** dos cards 6 e 2
  (`fetch_main_commits` e `fetch_history_runs`), então só os pacotes geram
  requisição nova. **Exige token com `read:packages`**: sem ele o GitHub responde
  401 e a rota devolve 502.
- `team`: um item por login de `TEAM_LOGINS`, **na ordem configurada**, mesmo sem
  atividade (zeros e avatar `https://github.com/<login>.png`). Logins comparados sem
  diferenciar maiúsculas; na saída, o login como o GitHub devolve. `prsOpen` = PRs
  abertos; `prsMerged` = PRs com `merged_at`; `commits` = `contributions` de
  `/contributors` (commits na branch padrão de contas vinculadas); `meetsRequirement`
  = **regra do trabalho**, pelo menos 1 PR de autoria (aberto, mergeado ou fechado
  sem merge). Pessoas fora do time são ignoradas. Busca `GET /pulls?state=all` (até
  100) e `GET /contributors` em paralelo; com `TEAM_LOGINS` vazio devolve `[]` sem
  chamar o GitHub.
- `pulls`: até `PULLS_LIMIT` PRs abertos (mais novo primeiro). Para cada PR, em
  paralelo: `GET /pulls/{n}` (`draft`, `mergeable_state`), `GET /commits/{sha}/check-runs`
  e `GET /pulls/{n}/reviews`. `checks`: o filtro padrão `latest` do GitHub já traz só a
  execução mais recente de cada check; não concluído → `pending`, `success` →
  `passed`, `skipped`/`neutral` não contam, qualquer outra conclusão → `failed`.
  `approvals` = revisores cujo último review (ignorando `COMMENTED`) é `APPROVED`.
  `badge`, nesta ordem:

  | `badge` | Quando |
  |---|---|
  | `draft` | PR em rascunho |
  | `conflict` | `mergeable_state` = `dirty` |
  | `checks_failed` | algum check falhou |
  | `waiting_checks` | algum check pendente, ou nenhum check contado |
  | `computing` | `mergeable_state` `unknown`, `null` ou desconhecido |
  | `needs_approval` | `mergeable_state` = `blocked` |
  | `ready` | `mergeable_state` `clean`, `unstable` ou `has_hooks` |

  `canApprove` = `ENABLE_WRITE_ACTIONS` + dono do token conhecido + autor diferente
  dele (sem diferenciar maiúsculas) + fora de rascunho + ainda sem aprovação vigente
  dele. `canMerge` = `ENABLE_WRITE_ACTIONS`, **mesmo com o PR bloqueado** (a demo
  mostra o GitHub recusando o merge). `GET /user` (dono do token) só é chamado com
  `GITHUB_TOKEN` e escrita ligada; sem PRs abertos, só a lista é buscada.
- Erros do GitHub seguem o mapeamento abaixo (ex.: rate limit → 503).

### Variáveis de ambiente (`api/.env`)

| Variável | Padrão | Descrição |
|---|---|---|
| `GITHUB_TOKEN` | `""` | Token classic com `public_repo` + `read:packages` (vazio = chamadas anônimas) |
| `GITHUB_OWNER` / `GITHUB_REPO` | `""` | Repositório monitorado |
| `GITHUB_WORKFLOW_FILE` | `ci.yml` | Arquivo do workflow de CI em `.github/workflows/` |
| `TEAM_LOGINS` | `[]` | Logins do time: `ana,bia,caio` (ou JSON `["ana","bia"]`) |
| `GHCR_IMAGES` | `["adec-api","adec-frontend"]` | Imagens no GHCR: `adec-api,adec-frontend` (ou JSON) |
| `GHCR_OWNER` | `""` | Dono das imagens no GHCR (vazio = `GITHUB_OWNER`; sempre em minúsculas) |
| `APP_VERSION` | `dev` | Versão em `/api/health`. No Docker vem da imagem; não defina no `.env` |
| `ENABLE_WRITE_ACTIONS` | `false` | Liga ações que escrevem no GitHub |
| `MERGE_METHOD` | `merge` | Método de merge dos PRs: `merge` ou `squash` |
| `PULLS_LIMIT` | `5` | Quantos PRs abertos listar (mínimo 1) |
| `HISTORY_LIMIT` | `20` | Quantos itens no histórico de runs/deploys (mínimo 1) |

## Desenvolvimento (sem Docker)

```bash
# API  ->  http://localhost:8000/api/health  (docs em /api/docs)
cd api
cp .env.example .env
uv sync
uv run uvicorn api.main:app --reload

# Frontend  ->  http://localhost:5173  (proxy /api -> localhost:8000, sem rewrite)
cd frontend
cp .env.example .env
npm ci
npm run dev
```

### Testes

```bash
cd api && uv run pytest
```

Os testes de pipeline usam JSON reais do GitHub em `tests/fixtures/github/`
(reduzidos aos campos usados) e derivam as variações alterando campos.
Os testes criam o app com `create_app(Settings(_env_file=None, ...))` e
`TestClient`, então não dependem do seu `.env`.

### Build do frontend e versão

```bash
cd frontend
APP_VERSION=1.2.3 npm run build   # padrão: "dev"
```

Gera `dist/version.json` (`{"version": "1.2.3"}`) e expõe o valor como
`import.meta.env.VITE_APP_VERSION`.

## Docker

```bash
cp .env.example .env              # GHCR_OWNER, IMAGE_TAG, APP_VERSION (raiz)
cp api/.env.example api/.env      # configuração da API

docker compose build              # constrói as duas imagens localmente
docker compose up -d              # sobe; o frontend espera a API ficar healthy
docker compose ps

curl localhost:8080/api/health    # API, via nginx
curl localhost:8080/              # index.html
curl -I localhost:8080/version.json   # Cache-Control: no-store

docker compose down
```

- Só o frontend publica porta (**8080**). A API (8000) fica na rede interna e é
  alcançada pelo nginx em `/api/` (o prefixo é mantido).
- Versão embutida nas imagens: `APP_VERSION=abc1234 docker compose up -d --build`
  (aparece em `/api/health`, em `/version.json` e no label
  `org.opencontainers.image.revision`).
- As imagens são `ghcr.io/${GHCR_OWNER}/adec-api` e `adec-frontend`
  (`GHCR_OWNER` precisa ser minúsculo). Com `image` + `build` juntos, o mesmo
  compose serve para `docker compose build` e `docker compose pull`.
- O nginx (`frontend/nginx.conf`) faz fallback de SPA, serve `index.html` e
  `version.json` com `no-store` e `/assets/` com cache `immutable` de 1 ano.

### Deploy contínuo simples

```bash
./scripts/watch-deploy.sh                    # pull + up -d a cada 20s
WATCH_INTERVAL=60 ./scripts/watch-deploy.sh  # intervalo configurável
```

Para imagens privadas, faça `docker login ghcr.io` antes.

> Antes de publicar no GHCR, troque o placeholder
> `org.opencontainers.image.source=https://github.com/alv4roso4res/REPO` nos dois
> Dockerfiles pelo repositório real.
