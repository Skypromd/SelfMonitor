#!/bin/sh
# Daily (or INTERVAL) pg_dumpall → gzip; rotate by mtime. For Compose: profile "backup".
set -eu
RETENTION="${BACKUP_RETENTION_DAYS:-14}"
INTERVAL="${BACKUP_INTERVAL_SEC:-86400}"
HOST="${POSTGRES_HOST:-postgres-master}"
USER="${POSTGRES_USER:-user}"
export PGPASSWORD="${POSTGRES_PASSWORD:?POSTGRES_PASSWORD must be set}"

mkdir -p /backups

echo "postgres-backup: waiting for ${HOST}..."
until pg_isready -h "$HOST" -U "$USER" -q; do sleep 5; done
echo "postgres-backup: started (interval ${INTERVAL}s, retention ${RETENTION} days)"

while true; do
  DATE=$(date +%Y-%m-%dT%H%M%S)
  TMP="/backups/pg_all_${DATE}.sql.gz.tmp"
  OUT="/backups/pg_all_${DATE}.sql.gz"
  if pg_dumpall -h "$HOST" -U "$USER" | gzip > "$TMP"; then
    mv "$TMP" "$OUT"
    echo "postgres-backup: wrote $OUT"
  else
    echo "postgres-backup: dump failed" >&2
    rm -f "$TMP"
  fi
  find /backups -name 'pg_all_*.sql.gz' -mtime +"$RETENTION" -delete
  sleep "$INTERVAL"
done
