#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

if [[ ! -d "$ROOT/.venv" ]]; then
  python3 -m venv "$ROOT/.venv"
  "$ROOT/.venv/bin/pip" install -r "$ROOT/requirements.txt"
fi

CERT_DIR="$ROOT/certs"
CERT="$CERT_DIR/cert.pem"
KEY="$CERT_DIR/key.pem"
if [[ ! -f "$CERT" || ! -f "$KEY" ]]; then
  mkdir -p "$CERT_DIR"
  if ! command -v openssl >/dev/null 2>&1; then
    echo "openssl is required to generate a local HTTPS certificate for Air (IMU) mode." >&2
    exit 1
  fi
  openssl req -x509 -newkey rsa:2048 \
    -keyout "$KEY" -out "$CERT" -days 825 -nodes \
    -subj "/CN=mouse-to-mac.local" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1" \
    2>/dev/null || openssl req -x509 -newkey rsa:2048 \
    -keyout "$KEY" -out "$CERT" -days 825 -nodes \
    -subj "/CN=mouse-to-mac.local"
  echo "Created self-signed TLS cert in host/certs/ (needed for phone IMU / Air mode)"
fi

exec env PYTHONUNBUFFERED=1 "$ROOT/.venv/bin/python3" "$ROOT/server.py"
