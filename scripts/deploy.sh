#!/usr/bin/env bash
# Deploy de produção. Roda na VM, executado pelo GitHub Actions via SSH ou manual.
set -euo pipefail

APP_DIR="${APP_DIR:-/home/ubuntu/pizzaria}"
BRANCH="${BRANCH:-main}"
BACKUP_DIR="${BACKUP_DIR:-/home/ubuntu/backups}"
HEALTH_HOST="${HEALTH_HOST:-pizzariadoaislan.com.br}"
KEEP_DAYS="${KEEP_DAYS:-30}"

log() { printf '\n==> %s\n' "$*"; }

cd "$APP_DIR"

log "Backup do SQLite"
mkdir -p "$BACKUP_DIR"
if [ -f db.sqlite3 ]; then
  backup="$BACKUP_DIR/db-$(date +%F-%H%M%S).sqlite3"
  sqlite3 db.sqlite3 ".backup $backup"
  find "$BACKUP_DIR" -name 'db-*.sqlite3' -mtime +"$KEEP_DAYS" -delete
  echo "backup: $backup"
fi

log "Atualizando codigo ($BRANCH)"
git fetch --prune origin "$BRANCH"
git pull --ff-only origin "$BRANCH"
git log -1 --oneline

log "Dependencias"
if ! .venv/bin/python -m pip --version >/dev/null 2>&1; then
  echo "pip ausente no venv; instalando com ensurepip"
  .venv/bin/python -m ensurepip --upgrade >/dev/null
fi
.venv/bin/python -m pip install --quiet -r requirements.txt

log "Migrations"
.venv/bin/python manage.py migrate --noinput

log "Static"
.venv/bin/python manage.py collectstatic --noinput

log "Reiniciando servico"
sudo systemctl restart pizzaria

log "Health check"
code=000
for _ in $(seq 1 20); do
  code=$(curl -s -o /dev/null -w '%{http_code}' -H "Host: $HEALTH_HOST" http://127.0.0.1:8001/ || true)
  case "$code" in
    200|301|302)
      echo "OK: HTTP $code"
      exit 0
      ;;
  esac
  sleep 2
done

echo "FALHA: health check retornou $code" >&2
sudo systemctl status pizzaria --no-pager >&2 || true
exit 1
