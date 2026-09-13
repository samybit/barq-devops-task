#!/usr/bin/env bash
set -euo pipefail

BACKUP_FILE="${1:-backups/latest.sql}"

if [ ! -f "$BACKUP_FILE" ]; then
    echo "[FAIL] Backup file '$BACKUP_FILE' not found!" >&2
    exit 1
fi

echo "Restoring PostgreSQL database from '$BACKUP_FILE'..."
docker compose exec -T postgres psql -U barq_app -d barq_tasks < "$BACKUP_FILE" > /dev/null

RECORD_COUNT=$(docker compose exec -T postgres psql -U barq_app -d barq_tasks -t -A -c "SELECT count(*) FROM records;")
echo "[SUCCESS] Database restored successfully. Current record count: $RECORD_COUNT"
