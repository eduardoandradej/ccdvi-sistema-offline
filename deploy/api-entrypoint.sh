#!/bin/sh
# Aplica migrações e inicia a API. A URL do banco vem de DVI_DATABASE_URL ou do
# segredo Podman montado em /run/secrets/dvi_database_url.
set -eu
if [ -z "${DVI_DATABASE_URL:-}" ] && [ -f /run/secrets/dvi_database_url ]; then
  DVI_DATABASE_URL="$(cat /run/secrets/dvi_database_url)"
  export DVI_DATABASE_URL
fi
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*' --workers "${DVI_WORKERS:-2}"
