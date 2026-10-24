#!/bin/sh
# Mantem a chave JWT estavel entre recriacoes do container sem exigir
# que o usuario configure outro .env apenas para uma demonstracao local.
set -eu

if [ -z "${SECRET_KEY:-}" ]; then
  secret_file=/run/auth-config/secret_key
  if [ ! -s "$secret_file" ]; then
    umask 077
    python -c 'import secrets; print(secrets.token_hex(32))' > "$secret_file"
  fi
  SECRET_KEY="$(cat "$secret_file")"
  export SECRET_KEY
fi

# Somente migrations incrementais: nao apaga tabelas nem volumes.
alembic upgrade head
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
