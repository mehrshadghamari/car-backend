#!/usr/bin/env bash
# Install Gunicorn (unix socket) + Celery worker/beat systemd units.
# Run as root from project root: sudo bash scripts/deploy/04-install-systemd.sh
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
VENV="$APP_DIR/venv"

if [[ ! -x "$VENV/bin/gunicorn" ]]; then
  echo "Missing venv at $VENV — run 02-setup-app.sh as $APP_USER first"
  exit 1
fi

echo "==> Installing systemd units (user=$APP_USER, workers=$GUNICORN_WORKERS)..."

cat >/etc/systemd/system/car-backend.socket <<EOF
[Unit]
Description=Car Backend Gunicorn socket

[Socket]
ListenStream=${SOCKET_PATH}
SocketUser=${APP_USER}
SocketGroup=www-data
SocketMode=0660

[Install]
WantedBy=sockets.target
EOF

cat >/etc/systemd/system/car-backend.service <<EOF
[Unit]
Description=Car Backend API (Gunicorn + Uvicorn)
Requires=car-backend.socket
After=network.target postgresql.service redis-server.service

[Service]
Type=notify
User=${APP_USER}
Group=www-data
WorkingDirectory=${APP_DIR}
Environment=PYTHONPATH=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
RuntimeDirectory=car-backend
RuntimeDirectoryMode=0755
ExecStart=${VENV}/bin/gunicorn src.main:app \\
  --workers ${GUNICORN_WORKERS} \\
  --worker-class uvicorn.workers.UvicornWorker \\
  --bind unix:${SOCKET_PATH} \\
  --access-logfile - \\
  --error-logfile - \\
  --timeout 120
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat >/etc/systemd/system/car-backend-celery-worker.service <<EOF
[Unit]
Description=Car Backend Celery worker
After=network.target redis-server.service postgresql.service car-backend.service

[Service]
Type=simple
User=${APP_USER}
Group=www-data
WorkingDirectory=${APP_DIR}
Environment=PYTHONPATH=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStart=${VENV}/bin/celery -A src.infrastructure.tasks.celery_app worker --loglevel=info --concurrency=1
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

cat >/etc/systemd/system/car-backend-celery-beat.service <<EOF
[Unit]
Description=Car Backend Celery beat scheduler
After=network.target redis-server.service car-backend-celery-worker.service

[Service]
Type=simple
User=${APP_USER}
Group=www-data
WorkingDirectory=${APP_DIR}
Environment=PYTHONPATH=${APP_DIR}
EnvironmentFile=${APP_DIR}/.env
ExecStart=${VENV}/bin/celery -A src.infrastructure.tasks.celery_app beat --loglevel=info
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

usermod -aG www-data "$APP_USER" 2>/dev/null || true

systemctl daemon-reload
systemctl enable car-backend.socket
systemctl restart car-backend.socket
systemctl enable car-backend.service
systemctl restart car-backend.service

if [[ "$USE_POSTGRES" == "true" ]]; then
  systemctl enable car-backend-celery-worker.service car-backend-celery-beat.service
  systemctl restart car-backend-celery-worker.service car-backend-celery-beat.service
else
  systemctl disable car-backend-celery-worker.service car-backend-celery-beat.service 2>/dev/null || true
fi

echo ""
echo "==> Service status:"
systemctl --no-pager status car-backend.socket car-backend.service --lines=5 || true
echo ""
echo "Test socket: curl --unix-socket ${SOCKET_PATH} http://localhost/health"
echo "Next: sudo bash scripts/deploy/05-install-nginx.sh"
