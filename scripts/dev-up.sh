#!/usr/bin/env bash
# Ambiente de DESENVOLVIMENTO local (sem contêineres), Ubuntu 24.04.
# Pré-requisitos: PostgreSQL 16 em execução, Python 3.12+, Node 22, uv (ou pip).
# Uso: scripts/dev-up.sh            -> instala dependências, migra, aplica seed e inicia API + frontend
#      scripts/dev-up.sh --no-seed  -> não executa o seed
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT/backend"

if [ -f .env ]; then set -a; . ./.env; set +a; fi
: "${DVI_DATABASE_URL:?Defina DVI_DATABASE_URL em backend/.env (ver .env.example)}"

if [ ! -d .venv ]; then
  if command -v uv >/dev/null; then uv venv -q .venv; uv pip install -q -p .venv -e '.[dev]';
  else python3 -m venv .venv; .venv/bin/pip install -q -e '.[dev]'; fi
fi
.venv/bin/alembic upgrade head
if [ "${1:-}" != "--no-seed" ]; then .venv/bin/python -m app.seed --demo-records; fi

cd "$ROOT/frontend"
[ -d node_modules ] || npm ci --no-audit --no-fund

cd "$ROOT/backend"
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 &
API_PID=$!
trap 'kill $API_PID 2>/dev/null' EXIT
cd "$ROOT/frontend"
echo "Frontend: http://$(hostname -I 2>/dev/null | awk '{print $1}'):5173  (API em 127.0.0.1:8000)"
npx vite --host 0.0.0.0 --port 5173 --strictPort
