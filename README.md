# ADEC

Monorepo do trabalho de DevOps (CI/CD):

| Pasta | O que é |
| --- | --- |
| `api/` | API em FastAPI (Python 3.13, gerenciada com `uv`, testes com `pytest`) |
| `frontend/` | Interface em React + Vite + TypeScript (`npm`) |
| `scripts/` | `watch-deploy.sh` (deploy contínuo da produção) e `check-local.sh` (o que o CI roda, localmente) |
| `docker-compose.yml` | Sobe `api` + `frontend` usando as imagens do GHCR |

## Como rodar localmente (desenvolvimento)

### Pré-requisitos

- [uv](https://docs.astral.sh/uv/) (instala o Python 3.13 sozinho)
- Node.js 22 e npm
- Um token do GitHub *classic* com os escopos `public_repo` e `read:packages`
  ([gerar aqui](https://github.com/settings/tokens/new?scopes=public_repo,read:packages&description=adec-backend)).
  Sem token a API funciona, mas com rate limit baixo e sem o card de versão.

### 1. Configurar a API (uma vez)

```bash
cp api/.env.example api/.env
```

Preencha no `api/.env`:

```bash
GITHUB_TOKEN=ghp_...
GITHUB_OWNER=alv4roso4res
GITHUB_REPO=adec
TEAM_LOGINS=alv4roso4res,GustaReis-bit,DrawnGZN
ENABLE_WRITE_ACTIONS=false     # true libera aprovar/mergear PR pelo painel
```

O `api/.env` está no `.gitignore`: nunca o commite.

### 2. Subir API e frontend (dois terminais)

```bash
# Terminal 1 — API em http://localhost:8000
cd api
uv sync
uv run uvicorn api.main:app --reload
```

```bash
# Terminal 2 — frontend em http://localhost:5173
cd frontend
cp .env.example .env     # só na primeira vez (VITE_API_URL=/api)
npm ci
npm run dev
```

O Vite encaminha `/api/*` para a API em `:8000`, então o navegador fala só com a
porta 5173 (sem CORS).

### 3. Testar

```bash
curl -s localhost:8000/api/health        # {"status":"ok","version":"dev"}
curl -s localhost:5173/api/health        # o mesmo, pelo proxy do Vite
```

A documentação interativa (Swagger) fica em **http://localhost:8000/api/docs**:
lá dá para executar cada rota pelo botão *Try it out*.

| Rota | Card do painel |
| --- | --- |
| `GET /api/health` | — (versão em execução) |
| `GET /api/pipeline/current` | 1. Status da main |
| `GET /api/pipeline/history?limit=` | 2. Últimos runs |
| `GET /api/pulls` | 3. PRs abertos |
| `GET /api/team` | 4. Integrantes |
| `GET /api/version` | 5. Versão publicada vs. main |
| `GET /api/commits?limit=` | 6. Commits da main |

### 4. Validar antes de abrir um PR

```bash
cd api && uv run pytest -v      # só os testes da API
bash scripts/check-local.sh     # tudo o que o build-test do CI roda
```

`bash scripts/check-local.sh --docker` também constrói as duas imagens (tag
`check-local`). **Não** use isso nem `docker compose build` na máquina de
produção (veja abaixo).

## Como rodar em produção (imagens do GHCR)

A "produção" é uma máquina com Docker que **só baixa** as imagens publicadas pelo
pipeline no GitHub Container Registry: `ghcr.io/alv4roso4res/adec-api` e
`ghcr.io/alv4roso4res/adec-frontend`. Nada é compilado nela.

### Pré-requisitos

- Docker com o plugin Compose (`docker compose version`)
- Este repositório clonado (só são usados o `docker-compose.yml`, os `.env` e o
  `scripts/watch-deploy.sh`)

### 1. Configurar (uma vez)

```bash
cp .env.example .env            # GHCR_OWNER=alv4roso4res, IMAGE_TAG=latest
cp api/.env.example api/.env    # mesmo conteúdo da seção de desenvolvimento
```

No `.env` da raiz, o `GHCR_OWNER` precisa estar **em minúsculas** e o
`IMAGE_TAG` em `latest`. Não defina `APP_VERSION` no `api/.env`: a versão vem
embutida na imagem.

As imagens são públicas, então não precisa de `docker login`. Se algum dia
ficarem privadas: `docker login ghcr.io` com um token que tenha `read:packages`.

### 2. Subir

```bash
docker compose pull             # baixa a latest das duas imagens
docker compose up -d            # sobe; o frontend espera a API ficar healthy
docker compose ps               # os dois serviços devem estar "running/healthy"
```

O painel fica em **http://localhost:8080** e o Swagger em
**http://localhost:8080/api/docs**. Só o frontend (nginx) publica porta, e só em
`127.0.0.1` (as rotas de aprovar/mergear usam o token do backend e não têm login:
ninguém mais na rede consegue abrir o painel); a API fica na rede interna do Docker
e é alcançada pelo nginx em `/api/`.

### 3. Conferir a versão no ar

```bash
curl -s localhost:8080/api/health    # "version" = SHA curto do último merge na main
curl -s localhost:8080/version.json  # mesmo SHA, do lado do frontend
docker buildx imagetools inspect ghcr.io/alv4roso4res/adec-api:latest | head -3
```

Os dois SHAs devem ser iguais ao último commit de merge da `main`.

### 4. Deploy contínuo (vigia)

O GHCR só guarda imagens; quem atualiza a produção é o `watch-deploy.sh`, que a
cada 20 s roda `docker compose pull && docker compose up -d` (o Compose só recria
o container cuja imagem mudou):

```bash
./scripts/watch-deploy.sh                        # em primeiro plano (Ctrl+C para parar)
WATCH_INTERVAL=60 ./scripts/watch-deploy.sh      # outro intervalo

# em segundo plano, sobrevivendo ao fechamento do terminal:
nohup ./scripts/watch-deploy.sh > watch-deploy.log 2>&1 &
tail -f watch-deploy.log
pkill -f watch-deploy.sh                         # para o vigia
```

Com o vigia rodando, um merge na `main` chega à produção sozinho em poucos
minutos: pipeline (~2 min) + até 20 s do vigia.

### 5. Rollback, logs e parada

```bash
# Fixar uma versão (rollback): no .env da raiz
IMAGE_TAG=sha-abc1234
docker compose pull && docker compose up -d     # volte para latest depois

docker compose logs -f api        # logs da API
docker compose logs -f frontend   # logs do nginx
docker compose up -d --force-recreate api   # depois de editar o api/.env
docker compose down               # para tudo
```

> **Na produção, nunca rode `docker compose build`.** Ele cria uma `latest`
> local por cima da do GHCR e o deploy contínuo deixa de refletir o pipeline.

## CI/CD

O [roadmap de implementação](contexto_projeto_adec.md#roadmap-de-execução) registra a
ordem dos próximos PRs e os critérios de conclusão de cada etapa.

Antes de enviar um PR, execute `bash scripts/check-local.sh`. Para validar também
os Dockerfiles, use `bash scripts/check-local.sh --docker` em uma máquina de
desenvolvimento. As imagens de validação recebem a tag `check-local`.

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

Como configurar e operar a máquina de produção: veja
[Como rodar em produção](#como-rodar-em-produção-imagens-do-ghcr).
