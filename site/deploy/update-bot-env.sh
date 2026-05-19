#!/usr/bin/env bash
# Обновляет /opt/projects/metr2-podkluch/.env с финальным URL политики
set -e
ENV_FILE="/opt/projects/metr2-podkluch/.env"
DOMAIN="https://metr-pod-klyuch.ru"
if grep -q "^PRIVACY_POLICY_URL=" "$ENV_FILE"; then
  sed -i "s|^PRIVACY_POLICY_URL=.*|PRIVACY_POLICY_URL=${DOMAIN}/privacy.html|" "$ENV_FILE"
else
  echo "PRIVACY_POLICY_URL=${DOMAIN}/privacy.html" >> "$ENV_FILE"
fi
systemctl restart metr2-bot
echo "Bot .env updated, service restarted"
