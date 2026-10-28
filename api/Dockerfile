# Binário do uv (versão fixa, a mesma do pyproject: uv_build>=0.13.6,<0.14)
FROM ghcr.io/astral-sh/uv:0.13.6 AS uv

# ---------- builder: resolve e instala o venv ----------
FROM python:3.13-slim AS builder
COPY --from=uv /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=0

WORKDIR /app

# Etapa 1: só dependências. Esta camada só é refeita se pyproject/uv.lock mudarem.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Etapa 2: o código do projeto (não-editável: o venv fica autocontido).
COPY README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable

# ---------- runtime ----------
FROM python:3.13-slim AS runtime

RUN groupadd --gid 1001 app \
 && useradd --uid 1001 --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
COPY --from=builder /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Declarado por último para que mudar a versão não invalide as camadas acima.
ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION

# TODO: trocar pelo repositório real (liga o pacote do GHCR ao repositório)
LABEL org.opencontainers.image.source="https://github.com/alv4roso4res/adec" \
      org.opencontainers.image.revision=$APP_VERSION

USER app
EXPOSE 8000

# A imagem slim não tem curl: usa urllib.
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
  CMD ["python", "-c", "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/health', timeout=2).status == 200 else 1)"]

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
