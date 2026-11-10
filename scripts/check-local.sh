#!/usr/bin/env bash
# Validações locais equivalentes às etapas de código do job build-test.
# Use --docker para construir imagens de validação sem alterar a latest.
set -euo pipefail

cd "$(dirname "$0")/.."

if [[ $# -gt 1 || ( $# -eq 1 && "$1" != "--docker" ) ]]; then
  echo "Uso: bash scripts/check-local.sh [--docker]" >&2
  exit 2
fi

echo "API — instalar dependências e executar testes"
(
  cd api
  uv sync --locked
  uv run --locked pytest -v
)

echo "Frontend — instalar dependências, lint e build"
(
  cd frontend
  npm ci
  npm run lint
  npm run build
)

echo "Scripts — validar sintaxe"
bash -n scripts/watch-deploy.sh scripts/check-local.sh

if [[ "${1:-}" == "--docker" ]]; then
  echo "Docker — construir imagens locais de validação"
  docker build --build-arg APP_VERSION=check-local -t adec-api:check-local ./api
  docker build --build-arg APP_VERSION=check-local -t adec-frontend:check-local ./frontend
fi

echo "Validações locais concluídas. O resultado do Actions deve ser conferido no PR."
