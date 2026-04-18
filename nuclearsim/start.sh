#!/usr/bin/env bash
# Launch the NuclearSim FastAPI server. The built React app is served from
# frontend/dist; the Python pipeline runs in-process on background threads.
set -euo pipefail

cd "$(dirname "$0")"

PORT="${PORT:-8000}"
HOST="${HOST:-0.0.0.0}"

if [[ -d frontend && ! -d frontend/dist ]]; then
  echo ">> building frontend..."
  (cd frontend && npm install --no-audit --no-fund && npm run build)
fi

exec uvicorn server:app --host "$HOST" --port "$PORT"
