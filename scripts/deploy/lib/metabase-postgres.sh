#!/usr/bin/env bash
# Allow Metabase (Docker) to connect to PostgreSQL on the same VPS.

ensure_metabase_pg_access() {
  local db_name="$1"
  local db_user="$2"
  local pg_hba pg_version_conf

  pg_hba="$(find /etc/postgresql -name pg_hba.conf 2>/dev/null | head -1 || true)"
  if [[ -z "$pg_hba" ]]; then
    echo "WARNING: pg_hba.conf not found — skip Postgres access tweak"
    return 0
  fi

  if ! grep -q "car-backend-metabase" "$pg_hba"; then
    cat >>"$pg_hba" <<EOF

# car-backend-metabase — allow Metabase (Docker/host) to reach PostgreSQL
host    ${db_name}    ${db_user}    127.0.0.1/32       scram-sha-256
host    ${db_name}    ${db_user}    ::1/128            scram-sha-256
host    ${db_name}    ${db_user}    172.16.0.0/12      scram-sha-256
host    ${db_name}    ${db_user}    192.168.0.0/16     scram-sha-256
EOF
    echo "    Updated $pg_hba"
  fi

  pg_version_conf="$(dirname "$pg_hba")/postgresql.conf"
  if [[ -f "$pg_version_conf" ]] && grep -q "^listen_addresses = 'localhost'" "$pg_version_conf"; then
    sed -i "s/^listen_addresses = 'localhost'/listen_addresses = 'localhost,*'/" "$pg_version_conf" || true
    echo "    Ensured Postgres listens for Docker bridge connections"
  fi

  systemctl reload postgresql 2>/dev/null || systemctl restart postgresql
}

test_metabase_db_connection() {
  local db_name="$1"
  local db_user="$2"
  local db_pass="$3"
  local host="${4:-127.0.0.1}"

  PGPASSWORD="$db_pass" psql -h "$host" -U "$db_user" -d "$db_name" -c "SELECT 1" >/dev/null 2>&1
}
