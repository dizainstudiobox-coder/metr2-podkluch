#!/usr/bin/env bash
# Шаг 2 после покупки домена: обновить nginx + получить Let's Encrypt SSL.
# Запускается ПОСЛЕ того как DNS A-запись metr-pod-klyuch.ru → 213.148.5.51 пропагировалась.
set -euo pipefail

DOMAIN="metr-pod-klyuch.ru"
WWW_DOMAIN="www.${DOMAIN}"
EMAIL="dizainstudiobox@gmail.com"
PROJECT_DIR="/opt/projects/metr2-podkluch"

echo "==> [1/5] Pull latest from repo"
git -C "$PROJECT_DIR" pull --ff-only

echo "==> [2/5] DNS pre-check"
SERVER_IP=$(curl -s -m 5 ifconfig.me)
DOMAIN_IP=$(dig +short "$DOMAIN" | tail -1)
echo "    server public IP: $SERVER_IP"
echo "    $DOMAIN resolves to: ${DOMAIN_IP:-(empty)}"
if [ "$DOMAIN_IP" != "$SERVER_IP" ]; then
  echo "    WARNING: DNS ещё не пропагировался. Подождите 5–30 минут после настройки и запустите снова."
  echo "    Продолжаю всё равно — certbot подскажет, если домен не резолвится."
fi

echo "==> [3/5] Install nginx config with server_name"
cp "$PROJECT_DIR/site/deploy/nginx-site.conf" /etc/nginx/sites-available/metr2-podkluch
ln -sf /etc/nginx/sites-available/metr2-podkluch /etc/nginx/sites-enabled/metr2-podkluch
rm -f /etc/nginx/sites-enabled/default
mkdir -p /var/www/certbot
nginx -t
systemctl reload nginx

echo "==> [4/5] Install certbot if missing"
if ! command -v certbot >/dev/null 2>&1; then
  apt-get update -qq
  apt-get install -qq -y certbot python3-certbot-nginx >/dev/null
fi

echo "==> [5/5] Obtain SSL certificate"
certbot --nginx \
  -d "$DOMAIN" -d "$WWW_DOMAIN" \
  --non-interactive --agree-tos -m "$EMAIL" \
  --redirect

echo ""
echo "==> Done. Сайт доступен:"
echo "    https://$DOMAIN"
echo "    https://$WWW_DOMAIN"
echo ""
echo "Сертификат обновится автоматически (systemd certbot.timer)."
