#!/usr/bin/env bash
# Restaura um backup gerado por scripts/backup.sh em um banco VAZIO e diretório de anexos VAZIO,
# e valida os hashes SHA-256 de todos os anexos contra os registrados no banco.
# Uso: scripts/restore.sh <arquivo .tar|.tar.gpg>
# Requer: DVI_DATABASE_URL (banco de destino, vazio) e DVI_STORAGE_DIR (diretório de destino, vazio).
set -euo pipefail
ARCHIVE="${1:?Informe o arquivo de backup}"
: "${DVI_DATABASE_URL:?}" "${DVI_STORAGE_DIR:?}"
PGURL="${DVI_DATABASE_URL/postgresql+psycopg:/postgresql:}"
[ -f "$ARCHIVE.sha256" ] && sha256sum -c "$ARCHIVE.sha256"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
if [[ "$ARCHIVE" == *.gpg ]]; then
  gpg --batch --decrypt --output "$WORK/backup.tar" "$ARCHIVE"
else
  cp "$ARCHIVE" "$WORK/backup.tar"
fi
tar -C "$WORK" -xf "$WORK/backup.tar"
B="$(find "$WORK" -maxdepth 1 -type d -name 'dvi-backup-*' | head -1)"
( cd "$B" && sha256sum -c MANIFEST.sha256 )

if [ -n "$(ls -A "$DVI_STORAGE_DIR" 2>/dev/null)" ]; then echo "DVI_STORAGE_DIR não está vazio." >&2; exit 1; fi
if [ "$(psql "$PGURL" -At -c "select count(*) from information_schema.tables where table_schema='public'")" != "0" ]; then
  echo "O banco de destino não está vazio." >&2; exit 1
fi
mkdir -p "$DVI_STORAGE_DIR"
pg_restore --no-owner --exit-on-error --dbname="$PGURL" "$B/database.dump"
tar -C "$DVI_STORAGE_DIR" -xf "$B/storage.tar"

FAIL=0
N=0
while read -r key hash; do
  N=$((N+1))
  actual="$(sha256sum "$DVI_STORAGE_DIR/$key" | cut -d' ' -f1)"
  if [ "$actual" != "$hash" ]; then echo "FALHA de integridade: $key"; FAIL=1; fi
done < <(psql "$PGURL" -At -F ' ' -c "select storage_key, sha256 from attachments")
[ $FAIL -eq 0 ] && echo "Restauração concluída: $N anexos verificados por SHA-256." || exit 2
