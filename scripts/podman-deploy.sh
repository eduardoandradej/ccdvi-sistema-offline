#!/usr/bin/env bash
# Implantação com Podman + Quadlet (systemd) em Ubuntu 24.04 — modo rootless do usuário atual.
# Não pressupõe podman-compose. Executar a partir da raiz do repositório.
#   scripts/podman-deploy.sh build     -> constrói as imagens localhost/dvi-api e localhost/dvi-web
#   scripts/podman-deploy.sh secrets   -> cria segredos Podman (senha do banco) interativamente
#   scripts/podman-deploy.sh install   -> instala unidades Quadlet e inicia os serviços
#   scripts/podman-deploy.sh seed      -> cria operação/bases/usuários de laboratório (dados fictícios)
#   scripts/podman-deploy.sh status
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION=0.1.0
QUADLET_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/containers/systemd"

case "${1:-}" in
  build)
    podman build -f "$ROOT/deploy/Containerfile.backend" -t "localhost/dvi-api:$VERSION" "$ROOT"
    podman build -f "$ROOT/deploy/Containerfile.web" -t "localhost/dvi-web:$VERSION" "$ROOT"
    podman pull docker.io/library/postgres:16-bookworm
    ;;
  secrets)
    read -rsp "Senha do banco PostgreSQL (não será exibida): " PW; echo
    [ ${#PW} -ge 12 ] || { echo "Use ao menos 12 caracteres."; exit 1; }
    printf '%s' "$PW" | podman secret create --replace dvi_db_password -
    printf 'postgresql+psycopg://dvi:%s@dvi-db:5432/dvi' "$PW" | podman secret create --replace dvi_database_url -
    unset PW
    ;;
  install)
    [ -f /etc/dvi/dvi.env ] || { echo "Crie /etc/dvi/dvi.env a partir de deploy/config/dvi.env.example"; exit 1; }
    mkdir -p "$QUADLET_DIR"
    cp "$ROOT"/deploy/quadlet/* "$QUADLET_DIR"/
    systemctl --user daemon-reload
    systemctl --user start dvi-db.service dvi-api.service dvi-web.service
    loginctl enable-linger "$USER" || true
    echo "Acesse: http://<IP-do-servidor>:8080"
    ;;
  seed)
    podman exec -it -e DVI_SEED_PASSWORD="${DVI_SEED_PASSWORD:-}" dvi-api python -m app.seed ${2:-}
    ;;
  status)
    systemctl --user --no-pager status dvi-db.service dvi-api.service dvi-web.service | grep -E "●|Active" || true
    podman ps --filter name=dvi-
    ;;
  *) sed -n '2,10p' "$0"; exit 1;;
esac
