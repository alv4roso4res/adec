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
│   ├── deps.py           get_settings / get_http_client (leem de request.app.state)
│   ├── errors.py         GitHubError + handler -> {"detail": ...}
│   ├── github/client.py  GitHubClient (casca: httpx.AsyncClient + owner/repo)
│   ├── routes/health.py  GET /api/health
│   ├── services/         (vazio, virá depois)
│   └── schemas/          (vazio, virá depois)
├── tests/                conftest.py, routes/, services/, fixtures/
├── Dockerfile
└── .env.example
```

- Tudo da API responde sob **`/api`** (inclusive `/api/docs` e `/api/openapi.json`).
- O `lifespan` cria **um** `httpx.AsyncClient` (base `https://api.github.com`,
  `Accept: application/vnd.github+json`, `X-GitHub-Api-Version`) em
  `app.state.http_client` e o fecha no shutdown. O header `Authorization:
  Bearer` só é enviado quando `GITHUB_TOKEN` não está vazio.
- Mapeamento de erros do GitHub (`GitHubError`): 401/403 de autenticação → **502**,
  rate limit (429, ou 403 com `rate_limited=True`) → **503**, 405 no merge → **409**,
  demais 5xx → 502, outros 4xx mantêm o status.

### Variáveis de ambiente (`api/.env`)

| Variável | Padrão | Descrição |
|---|---|---|
| `GITHUB_TOKEN` | `""` | Token do GitHub (vazio = chamadas anônimas) |
| `GITHUB_OWNER` / `GITHUB_REPO` | `""` | Repositório monitorado |
| `TEAM_LOGINS` | `[]` | Logins do time: `ana,bia,caio` (ou JSON `["ana","bia"]`) |
| `GHCR_PACKAGE` | `""` | Nome do pacote no GHCR |
| `APP_VERSION` | `dev` | Versão em `/api/health`. No Docker vem da imagem; não defina no `.env` |
| `ENABLE_WRITE_ACTIONS` | `false` | Liga ações que escrevem no GitHub |
| `CACHE_TTL_SECONDS` | `15` | TTL do cache das respostas do GitHub |

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
