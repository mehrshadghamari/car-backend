#!/usr/bin/env bash
# Find a free TCP port for the local API (prefers 8000).
find_free_port() {
  local p
  for p in "$@"; do
    if ! ss -tln 2>/dev/null | grep -q ":${p} "; then
      echo "$p"
      return 0
    fi
  done
  return 1
}

describe_port_blocker() {
  local port="$1"
  local pid scope
  pid="$(lsof -t -iTCP:"${port}" -sTCP:LISTEN 2>/dev/null | head -1 || true)"
  [ -n "$pid" ] || return 0
  scope="$(tr -d '\0' < "/proc/${pid}/cgroup" 2>/dev/null | grep -o 'app-org[^/]*' | head -1 || true)"
  scope="${scope%.scope}"
  echo "Port ${port} is held by PID ${pid} (cannot kill from this shell)."
  if [[ "$scope" == app-org.chromium.* ]]; then
    echo "  Cause: process runs inside Cursor/Chromium sandbox (${scope})."
    echo "  Fix options:"
    echo "    1) Close the Cursor terminal tab that started uvicorn"
    echo "    2) Restart Cursor IDE"
    echo "    3) Use another port: PORT=8001 bash scripts/local-up.sh"
    if [ -n "$scope" ]; then
      echo "    4) From an external terminal (outside Cursor):"
      echo "         systemctl --user stop ${scope}.scope"
    fi
  fi
}
