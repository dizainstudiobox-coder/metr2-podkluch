#!/usr/bin/env bash
# Установщик статического сайта МЕТР² ПОД КЛЮЧ.
# Запускать от root на сервере. Идемпотентен.
set -euo pipefail

PROJECT_DIR="/opt/projects/metr2-podkluch"
NGINX_CONF_SRC="$PROJECT_DIR/site/deploy/nginx-site.conf"
NGINX_CONF_DST="/etc/nginx/sites-available/metr2-podkluch"
NGINX_ENABLED="/etc/nginx/sites-enabled/metr2-podkluch"

echo "==> [1/5] Nginx packages"
if ! command -v nginx >/dev/null 2>&1; then
  apt-get update -qq
  apt-get install -qq -y nginx >/dev/null
fi

echo "==> [2/5] Pull latest from repo"
if [ -d "$PROJECT_DIR/.git" ]; then
  git -C "$PROJECT_DIR" pull --ff-only
else
  echo "Error: $PROJECT_DIR не найден. Сначала запустите install.sh бота." >&2
  exit 1
fi

echo "==> [3/5] Disable default site"
rm -f /etc/nginx/sites-enabled/default

echo "==> [4/5] Install site config"
cp "$NGINX_CONF_SRC" "$NGINX_CONF_DST"
ln -sf "$NGINX_CONF_DST" "$NGINX_ENABLED"
nginx -t

echo "==> [5/5] Reload nginx"
systemctl reload nginx || systemctl restart nginx
systemctl status nginx --no-pager | head -10

SERVER_IP=$(curl -s -m 5 ifconfig.me || echo "your-server-ip")
echo ""
echo "==> Installed. Сайт доступен по адресу:"
echo "    http://${SERVER_IP}"
echo ""
echo "    После покупки и привязки домена:"
echo "      certbot --nginx -d ваш-домен.ru"
echo ""
echo "    Обновление контента:"
echo "      cd $PROJECT_DIR && git pull   # перезапуск nginx не нужен"
