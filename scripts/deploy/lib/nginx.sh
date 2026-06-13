#!/usr/bin/env bash
# Nginx helpers for Debian VPS deploy.

nginx_has_working_ipv6() {
  [[ -f /proc/net/if_inet6 ]] || return 1
  if sysctl -n net.ipv6.conf.all.disable_ipv6 2>/dev/null | grep -qx '1'; then
    return 1
  fi
  ip -6 addr show scope global 2>/dev/null | grep -q 'inet6'
}

nginx_listen_http() {
  echo "    listen 80;"
  if nginx_has_working_ipv6; then
    echo "    listen [::]:80;"
  fi
}

nginx_free_port_80() {
  if systemctl is-active --quiet apache2 2>/dev/null; then
    echo "==> Stopping Apache (conflicts with nginx on port 80)..."
    systemctl stop apache2
    systemctl disable apache2 || true
  fi

  if ss -tlnH 2>/dev/null | grep -q ':80 '; then
    local blocker
    blocker="$(ss -tlnH sport = :80 2>/dev/null | head -1 || true)"
    if [[ -n "$blocker" ]] && ! echo "$blocker" | grep -qi nginx; then
      echo "WARNING: Port 80 is already in use:"
      echo "  $blocker"
      echo "  Stop that service before continuing."
    fi
  fi
}

nginx_write_baseline_site() {
  local site="/etc/nginx/sites-available/000-car-backend-baseline"
  cat >"$site" <<EOF
server {
$(nginx_listen_http)
    server_name _;
    root /var/www/html;
    index index.nginx-debian.html index.html;
    location / {
        try_files \$uri \$uri/ =404;
    }
}
EOF

  mkdir -p /var/www/html
  if [[ ! -f /var/www/html/index.html && -f /usr/share/nginx/html/index.html ]]; then
    cp /usr/share/nginx/html/index.html /var/www/html/index.html 2>/dev/null || true
  fi

  rm -f /etc/nginx/sites-enabled/default
  rm -f /etc/nginx/sites-enabled/default-catchall
  ln -sf "$site" /etc/nginx/sites-enabled/000-car-backend-baseline
}

nginx_test_and_start() {
  local action="${1:-restart}"

  if ! nginx -t 2>/tmp/nginx-test.err; then
    echo "nginx config test failed (IPv6 may be the cause). Retrying without [::] listeners..."
    sed -i '/listen \[::\]:/d' /etc/nginx/sites-enabled/* /etc/nginx/sites-available/* 2>/dev/null || true
    sed -i '/listen \[::\]:/d' /etc/nginx/conf.d/* 2>/dev/null || true
    nginx -t
  fi

  systemctl enable nginx
  case "$action" in
    reload)
      if systemctl is-active --quiet nginx; then
        systemctl reload nginx
      else
        systemctl start nginx
      fi
      ;;
    *)
      systemctl restart nginx
      ;;
  esac
}

ensure_nginx_baseline() {
  echo "==> Preparing nginx baseline config..."
  nginx_free_port_80
  nginx_write_baseline_site
  nginx_test_and_start restart
  echo "    nginx is running (baseline site on port 80)"
}

nginx_diagnose() {
  echo "=== nginx status ==="
  systemctl status nginx --no-pager -l || true
  echo ""
  echo "=== nginx -t ==="
  nginx -t 2>&1 || true
  echo ""
  echo "=== port 80 ==="
  ss -tlnp | grep ':80 ' || echo "(nothing on port 80)"
  echo ""
  echo "=== sites-enabled ==="
  ls -la /etc/nginx/sites-enabled/ 2>/dev/null || true
  echo ""
  echo "=== recent nginx journal ==="
  journalctl -xeu nginx.service --no-pager -n 30 2>/dev/null || true
}
