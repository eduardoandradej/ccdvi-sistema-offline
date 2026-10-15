#!/usr/bin/env bash
# Teste automatizado de backup -> restauração em ambiente limpo -> verificação de hashes e contagens.
# Uso: SRC_URL=... SRC_STORAGE=... ADMIN_PSQL="sudo -u postgres psql" scripts/test-backup-restore.sh
# Cria e remove um banco temporário "dvi_restore_test" (o papel do banco precisa de CREATEDB ou use ADMIN_PSQL).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
: "${SRC_URL:?URL do banco de origem (postgresql+psycopg://...)}" "${SRC_STORAGE:?diretório de anexos de origem}"
ADMIN_PSQL="${ADMIN_PSQL:-sudo -u postgres psql}"
TMP="$(mktemp -d)"
DST_URL="${SRC_URL%/*}/dvi_restore_test"
trap '$ADMIN_PSQL -q -c "DROP DATABASE IF EXISTS dvi_restore_test" >/dev/null; rm -rf "$TMP"' EXIT
$ADMIN_PSQL -q -c "DROP DATABASE IF EXISTS dvi_restore_test" -c "CREATE DATABASE dvi_restore_test OWNER dvi"

ARCHIVE="$(DVI_DATABASE_URL="$SRC_URL" DVI_STORAGE_DIR="$SRC_STORAGE" "$ROOT/scripts/backup.sh" "$TMP/backups" 2>/dev/null)"
DVI_DATABASE_URL="$DST_URL" DVI_STORAGE_DIR="$TMP/storage" "$ROOT/scripts/restore.sh" "$ARCHIVE"

Q="select (select count(*) from am_cases),(select count(*) from pm_cases),(select count(*) from attachments),
   (select count(*) from physical_marks),(select count(*) from effects),(select count(*) from match_reviews)"
A="$(psql "${SRC_URL/postgresql+psycopg:/postgresql:}" -At -c "$Q")"
B="$(psql "${DST_URL/postgresql+psycopg:/postgresql:}" -At -c "$Q")"
echo "origem:  $A"; echo "destino: $B"
[ "$A" = "$B" ] && echo "OK: backup/restore validado" || { echo "FALHA: contagens diferentes"; exit 1; }
