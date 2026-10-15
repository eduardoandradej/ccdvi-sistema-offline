#!/usr/bin/env bash
# Backup consistente: dump do PostgreSQL + diretório de anexos + manifesto SHA-256.
# Criptografia: se DVI_BACKUP_GPG_RECIPIENT estiver definido, o pacote é cifrado com GnuPG
# (chave pública do destinatário; nenhuma chave é embutida no projeto).
# Uso: scripts/backup.sh <diretorio-destino>
# Requer: pg_dump compatível, DVI_DATABASE_URL (formato SQLAlchemy ou libpq) e DVI_STORAGE_DIR.
set -euo pipefail
DEST="${1:?Informe o diretório de destino}"
: "${DVI_DATABASE_URL:?}" "${DVI_STORAGE_DIR:?}"
PGURL="${DVI_DATABASE_URL/postgresql+psycopg:/postgresql:}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
mkdir -p "$WORK/dvi-backup-$STAMP"
B="$WORK/dvi-backup-$STAMP"

pg_dump --format=custom --no-owner --file="$B/database.dump" "$PGURL"
tar -C "$DVI_STORAGE_DIR" -cf "$B/storage.tar" .
psql "$PGURL" -At -c "select storage_key || '  ' || sha256 from attachments order by storage_key" > "$B/attachments.sha256-db"
( cd "$B" && sha256sum database.dump storage.tar attachments.sha256-db > MANIFEST.sha256 )
cat > "$B/INFO.txt" <<INFO
Backup Sistema DVI Offline
Data (UTC): $STAMP
Versão do esquema: $(psql "$PGURL" -At -c "select version_num from alembic_version")
Anexos: $(wc -l < "$B/attachments.sha256-db")
INFO

mkdir -p "$DEST"
OUT="$DEST/dvi-backup-$STAMP.tar"
tar -C "$WORK" -cf "$OUT" "dvi-backup-$STAMP"
if [ -n "${DVI_BACKUP_GPG_RECIPIENT:-}" ]; then
  gpg --batch --yes --encrypt --recipient "$DVI_BACKUP_GPG_RECIPIENT" --output "$OUT.gpg" "$OUT"
  shred -u "$OUT" 2>/dev/null || rm -f "$OUT"
  OUT="$OUT.gpg"
else
  echo "AVISO: backup NÃO criptografado (defina DVI_BACKUP_GPG_RECIPIENT)." >&2
fi
sha256sum "$OUT" > "$OUT.sha256"
echo "$OUT"
