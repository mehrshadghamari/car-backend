#!/usr/bin/env bash
# Nginx reverse proxy to Gunicorn unix socket for car-alert.ir
# Run as root: sudo bash scripts/deploy/05-install-nginx.sh
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Run as root: sudo bash $0"
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/scripts/deploy/lib/common.sh"
load_deploy_config

SOCKET_PATH="/run/car-backend/car-backend.sock"
SITE="/etc/nginx/sites-available/car-backend"

echo "==> Installing Nginx site for ${DOMAIN}..."

cat >"$SITE" <<EOF
upstream car_backend_app {
    server unix:${SOCKET_PATH};
}

server {
    listen 80;
    listen [::]:80;
    server_name ${DOMAIN} www.${DOMAIN};

    client_max_body_size 20M;

    access_log /var/log/nginx/car-backend.access.log;
    error_log  /var/log/nginx/car-backend.error.log;

    location /static/ {
        alias ${APP_DIR}/static/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    location /portal/ {
        alias ${APP_DIR}/user-portal/;
        try_files \$uri \$uri/ /portal/index.html;
    }

    location / {
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_redirect off;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_pass http://car_backend_app;
        proxy_read_timeout 120s;
    }
}
EOF

ln -sf "$SITE" /etc/nginx/sites-enabled/car-backend
rm -f /etc/nginx/sites-enabled/default

nginx -t
systemctl reload nginx

echo ""
echo "Nginx configured for http://${DOMAIN}"
echo ""
echo "HTTPS (certbot + nginx plugin):"
echo "  sudo bash ${APP_DIR}/scripts/deploy/06-install-ssl.sh"
echo ""
echo "Certbot auto-renewal is handled by certbot.timer on Debian."
