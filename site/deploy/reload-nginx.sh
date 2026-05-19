#!/usr/bin/env bash
set -e
cp /opt/projects/metr2-podkluch/site/deploy/nginx-site.conf /etc/nginx/sites-available/metr2-podkluch
nginx -t
systemctl reload nginx
echo "nginx reloaded with new cache rules"
