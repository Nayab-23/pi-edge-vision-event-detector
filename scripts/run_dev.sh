#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_dir"

if [[ -f ".env" ]]; then
  set -a
  . ./.env
  set +a
fi

exec .venv/bin/uvicorn app.main:app --host "${PIVED_HOST:-0.0.0.0}" --port "${PIVED_PORT:-8080}" --reload
