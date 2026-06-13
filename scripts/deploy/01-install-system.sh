#!/usr/bin/env bash
# Install Python 3.10+, PostgreSQL, Redis, Nginx, Certbot on Debian VPS.
# Tested for Debian 11 (bullseye) and Debian 12 (bookworm).
# Run as root: sudo bash scripts/deploy/01-install-system.sh
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "Run as root: sudo bash $0"
  exit 1
fi

if [[ ! -f /etc/debian_version ]]; then
  echo "This script is for Debian only (/etc/debian_version not found)."
  exit 1
fi

DEBIAN_VERSION="$(cut -d. -f1 /etc/debian_version 2>/dev/null || cat /etc/debian_version)"
echo "==> Debian ${DEBIAN_VERSION} detected"

echo "==> Updating apt..."
export DEBIAN_FRONTEND=noninteractive
apt update
apt install -y \
  ca-certificates \
  curl \
  git \
  nginx \
  redis-server \
  postgresql \
  postgresql-contrib \
  python3 \
  python3-venv \
  python3-dev \
  python3-pip \
  build-essential \
  libpq-dev \
  openssl \
  certbot \
  python3-certbot-nginx

# Optional firewall (install if you use ufw)
if ! command -v ufw >/dev/null 2>&1; then
  apt install -y ufw || true
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
# shellcheck disable=SC1091
source "$ROOT/scripts/deploy/lib/common.sh"
# shellcheck disable=SC1091
source "$ROOT/scripts/deploy/lib/nginx.sh"
ensure_python310_debian

echo "==> Enabling Redis + PostgreSQL + Certbot timer..."
systemctl enable --now redis-server
systemctl enable --now postgresql
ensure_nginx_baseline
systemctl enable --now certbot.timer 2>/dev/null || true

if command -v ufw >/dev/null 2>&1; then
  echo "==> Firewall (SSH + HTTP/HTTPS)..."
  ufw allow OpenSSH >/dev/null 2>&1 || ufw allow 22/tcp
  ufw allow 'Nginx Full' >/dev/null 2>&1 || { ufw allow 80/tcp; ufw allow 443/tcp; }
  ufw --force enable || true
fi

echo ""
echo "System packages installed."
echo "Python: $($PYTHON --version)"
echo "Next: clone repo to /opt/car-backend, then run vps-first-deploy.sh"
