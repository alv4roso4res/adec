# ADEC

Monorepo do trabalho de DevOps (CI/CD):

| Pasta | O que é |
| --- | --- |
| `api/` | API em FastAPI (Python 3.13, gerenciada com `uv`, testes com `pytest`) |
| `frontend/` | Interface em React + Vite + TypeScript (`npm`) |
| `scripts/` | `watch-deploy.sh`, o "deploy contínuo" da máquina de produção |
| `docker-compose.yml` | Sobe `api` + `frontend` usando as imagens do GHCR |

## CI/CD

O pipeline está em [`.github/workflows/ci.yml`](.github/workflows/ci.yml) (GitHub Actions).

### Gatilhos

| Evento | O que roda |
| --- | --- |
| `pull_request` para `main` | `build-test` |
| `push` na `main` (merge) | `build-test` e depois `deploy` |

Runs de um mesmo PR se cancelam (só vale o mais recente). Pushes na `main` nunca são
cancelados: esperam o run em andamento terminar.

### Jobs

- **`build-test`**: valida tudo sem publicar nada.
  1. API: `uv sync --locked` e `uv run pytest -v`.
  2. Frontend: `npm ci`, `npm run lint` e `npm run build`.
  3. Docker: constrói as imagens da API e do frontend com `push: false`. Isso
     valida os Dockerfiles no PR e aquece o cache (`type=gha`, um escopo por imagem)
     que o `deploy` reaproveita.
- **`deploy`** (só em push na `main`, só se o `build-test` passou): publica no GHCR.
  1. Faz login no `ghcr.io` com o `GITHUB_TOKEN` (permissão `packages: write` só neste job).
  2. Constrói e publica `adec-api` e `adec-frontend` com a tag `sha-<7 chars>`.
  3. **Depois das duas publicações**, promove a tag `latest` de cada imagem
     (`docker buildx imagetools create`).
  4. Escreve no resumo do run a tabela de imagens/tags publicadas.

### Estratégia de tags

| Tag | Quem cria | Para quê |
| --- | --- | --- |
| `sha-<7 chars>` | build+push do `deploy` | Imutável: identifica o commit exato. Serve para rollback |
| `latest` | passo "Promover a tag latest" | Móvel: é o que a produção observa |

O build+push **nunca** publica `latest`. Ela só é movida no fim, quando as duas imagens
do mesmo commit já estão no registro. Assim a produção não recebe uma imagem nova
junto de outra velha. O `APP_VERSION` embutido nas imagens é o mesmo SHA curto
(aparece em `/api/health` e no `version.json` do frontend).

### Fluxo

```text
PR ──────► build-test (API + frontend + docker build, sem push)

merge ───► build-test ──► deploy ──► GHCR ──► watch-deploy.sh ──► containers
 (main)                   │            ▲        (a cada 20s)       (compose up -d)
                          │            │
                          ├─ push :sha-<7 chars> (api e frontend)
                          └─ promove :latest (só depois dos dois pushes)
```

### Produção

Na máquina de produção:

```bash
cp .env.example .env     # ajuste GHCR_OWNER (minúsculo) e demais variáveis
cp api/.env.example api/.env
./scripts/watch-deploy.sh                    # a cada 20s
WATCH_INTERVAL=60 ./scripts/watch-deploy.sh  # ou outro intervalo
```

A cada ciclo o script roda `docker compose pull && docker compose up -d` na tag
`latest`; o Compose só recria os containers cuja imagem mudou. Para fixar uma versão
(ou fazer rollback), defina `IMAGE_TAG=sha-<7 chars>` no `.env`.

> Os pacotes criados pelo `GITHUB_TOKEN` nascem **privados** no GHCR. Ou torne-os
> públicos nas configurações do pacote, ou rode `docker login ghcr.io` na produção.
