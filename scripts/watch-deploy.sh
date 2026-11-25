#!/usr/bin/env bash
# Deploy contínuo simples, sem tag "latest": a cada WATCH_INTERVAL segundos
# descobre o último commit da main e sobe a imagem sha-<7 chars> dele.
# Enquanto o pipeline ainda não publicou essa imagem, o pull falha e a
# produção continua na versão anterior. Rode na raiz do repo (ou de qualquer lugar).
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

log "observando a main a cada ${INTERVAL}s (Ctrl+C para parar)"

while true; do
  if git fetch -q origin main; then
    # Exportada, vale mais que o IMAGE_TAG do .env para o docker compose.
    export IMAGE_TAG="sha-$(git rev-parse origin/main | cut -c1-7)"
    if docker compose pull -q && docker compose up -d; then
      log "ok ($IMAGE_TAG)"
    else
      log "$IMAGE_TAG ainda não publicada (ou pull/up falhou); tentando de novo em ${INTERVAL}s"
    fi
  else
    log "git fetch falhou; tentando de novo em ${INTERVAL}s"
  fi
  # sleep em background + wait: deixa o Ctrl+C interromper na hora.
  sleep "$INTERVAL" &
  wait $!
done
