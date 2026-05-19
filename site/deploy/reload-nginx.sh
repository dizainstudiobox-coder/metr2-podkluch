#!/usr/bin/env bash
set -e
PROJECT_DIR="/opt/projects/metr2-podkluch"

echo "==> [1/3] Install fresh nginx config (HTTP only)"
cp "$PROJECT_DIR/site/deploy/nginx-site.conf" /etc/nginx/sites-available/metr2-podkluch
nginx -t
systemctl reload nginx

echo "==> [2/3] Re-attach SSL via certbot --reinstall"
certbot --nginx \
  -d metr-pod-klyuch.ru -d www.metr-pod-klyuch.ru \
  --non-interactive --redirect --reinstall

echo "==> [3/3] Final reload"
systemctl reload nginx
echo ""
echo "Done. HTTPS снова работает: https://metr-pod-klyuch.ru"
