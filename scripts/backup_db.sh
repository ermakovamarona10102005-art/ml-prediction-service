#!/bin/bash
set -euo pipefail
umask 077
cd /
BACKUP_DIR=/var/backups/ml-predictions
install -d -m 0700 "$BACKUP_DIR"
exec 9>"$BACKUP_DIR/.backup.lock"
flock -n 9 || exit 0
stamp=$(date -u +%Y%m%d_%H%M%S)
target="$BACKUP_DIR/ml_predictions_$stamp.dump"
temp=$(mktemp "$BACKUP_DIR/.pending.XXXXXX")
trap 'rm -f -- "$temp"' EXIT
runuser -u postgres -- pg_dump --format=custom --dbname=ml_predictions > "$temp"
pg_restore --list "$temp" > /dev/null
mv -- "$temp" "$target"
sha256sum "$target" > "$target.sha256"
find "$BACKUP_DIR" -maxdepth 1 -type f -name 'ml_predictions_*.dump*' -mtime +7 -delete
echo "$(date -u --iso-8601=seconds) Backup created: $target"
