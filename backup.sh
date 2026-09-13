#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${1:-backups}"
mkdir -p "$BACKUP_DIR"

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.sql"
LATEST_FILE="${BACKUP_DIR}/latest.sql"

echo "Creating PostgreSQL backup from container 'postgres'..."
docker compose exec -T postgres pg_dump -U barq_app --clean --if-exists barq_tasks > "$BACKUP_FILE"

cp "$BACKUP_FILE" "$LATEST_FILE"

echo "[SUCCESS] Backup saved to: $BACKUP_FILE"
echo "Backup size: $(wc -c < "$BACKUP_FILE") bytes"
