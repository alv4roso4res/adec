#!/usr/bin/env bash
# Deploy contínuo simples: a cada WATCH_INTERVAL segundos baixa as imagens do
# GHCR e sobe o que mudou. Rode na raiz do repo (ou de qualquer lugar).
#
#   ./scripts/watch-deploy.sh                    # a cada 20s
#   WATCH_INTERVAL=60 ./scripts/watch-deploy.sh  # a cada 60s
#
# Se as imagens forem privadas: `docker login ghcr.io` antes.
set -uo pipefail

cd "$(dirname "$0")/.."

INTERVAL="${WATCH_INTERVAL:-20}"

log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }

trap 'log "encerrando"; exit 0' INT TERM

log "observando imagens a cada ${INTERVAL}s (Ctrl+C para parar)"

while true; do
  if docker compose pull -q && docker compose up -d; then
    log "ok"
  else
    log "falhou (pull/up); tentando de novo em ${INTERVAL}s"
  fi
  # sleep em background + wait: deixa o Ctrl+C interromper na hora.
  sleep "$INTERVAL" &
  wait $!
done
