#!/usr/bin/env bash
# RagStudio launcher: ./rs <group> <command> [flags]
# Interpreter: $RAGSTUDIO_PYTHON, then the conda env `ragstudio`, then python3.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${RAGSTUDIO_PYTHON:-}"
if [ -z "$PY" ]; then
  for base in /opt/miniconda3 "$HOME/miniconda3" "$HOME/miniforge3" "$HOME/anaconda3" "$HOME/mambaforge"; do
    if [ -x "$base/envs/ragstudio/bin/python" ]; then PY="$base/envs/ragstudio/bin/python"; break; fi
  done
fi
PY="${PY:-python3}"
cd "$ROOT"
exec "$PY" -m ragstudio "$@"
