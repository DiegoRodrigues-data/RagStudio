#!/usr/bin/env bash
# Everything CI runs: backend lint + offline tests, then frontend typecheck + lint + build.
#   scripts/check.sh            all
#   scripts/check.sh --backend  Python only
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
PY="${RAGSTUDIO_PYTHON:-}"
if [ -z "$PY" ]; then
  for base in /opt/miniconda3 "$HOME/miniconda3" "$HOME/miniforge3" "$HOME/anaconda3" "$HOME/mambaforge"; do
    if [ -x "$base/envs/ragstudio/bin/python" ]; then PY="$base/envs/ragstudio/bin/python"; break; fi
  done
fi
PY="${PY:-python3}"
echo "== ruff";   "$PY" -m ruff check ragstudio tests
echo "== pytest"; RAGSTUDIO_PROVIDER=mock "$PY" -m pytest tests -q
if [ "${1:-}" = "--backend" ]; then exit 0; fi
if [ ! -d Frontend/node_modules ]; then
  echo "== frontend skipped: Frontend/node_modules missing (run ./run.sh or 'cd Frontend && npm install')"
  exit 0
fi
echo "== frontend typecheck + lint"; (cd Frontend && npm run --silent check)
echo "== frontend build";            (cd Frontend && npm run --silent build >/dev/null && echo "build ok")
