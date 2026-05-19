#!/usr/bin/env bash
# Установщик бота МЕТР² ПОД КЛЮЧ на VPS.
# Запускается один раз от root. Идемпотентен — можно перезапускать.
set -euo pipefail

REPO_URL="${REPO_URL:?REPO_URL must be set, e.g. https://USER:PAT@github.com/.../metr2-podkluch.git}"
BOT_TOKEN="${BOT_TOKEN:?BOT_TOKEN must be set}"
ADMIN_USERNAME="${ADMIN_USERNAME:-Dmitry_Dolgoter}"

PROJECT_DIR="/opt/projects/metr2-podkluch"
SERVICE_NAME="metr2-bot"

echo "==> [1/6] System packages"
apt-get update -qq
apt-get install -qq -y python3-venv python3-pip git >/dev/null

echo "==> [2/6] Clone or update repo"
if [ -d "$PROJECT_DIR/.git" ]; then
  git -C "$PROJECT_DIR" pull --ff-only
else
  mkdir -p /opt/projects
  git clone "$REPO_URL" "$PROJECT_DIR"
fi

echo "==> [3/6] Python venv + dependencies"
cd "$PROJECT_DIR"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

echo "==> [4/6] Environment file"
mkdir -p /var/lib/metr2-podkluch
cat > "$PROJECT_DIR/.env" <<ENV
BOT_TOKEN=${BOT_TOKEN}
ADMIN_USERNAME=${ADMIN_USERNAME}
BOT_DB_PATH=/var/lib/metr2-podkluch/metr2.sqlite3
ENV
chmod 600 "$PROJECT_DIR/.env"

echo "==> [5/6] systemd service"
cp "$PROJECT_DIR/deploy/metr2-bot.service" "/etc/systemd/system/${SERVICE_NAME}.service"
systemctl daemon-reload
systemctl enable "$SERVICE_NAME" >/dev/null

echo "==> [6/6] Restart service"
systemctl restart "$SERVICE_NAME"
sleep 3
systemctl status "$SERVICE_NAME" --no-pager | head -20
echo ""
echo "==> Last 10 log lines:"
journalctl -u "$SERVICE_NAME" --no-pager -n 10

echo ""
echo "==> Installed."
echo "    Logs:    journalctl -u $SERVICE_NAME -f"
echo "    Update:  cd $PROJECT_DIR && git pull && systemctl restart $SERVICE_NAME"
