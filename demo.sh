#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if [[ ! -x .venv/bin/python ]]; then
  echo 'Chưa có .venv. Xem docs/DEMO_GUIDE.md để cài môi trường.' >&2
  exit 1
fi
export PATH="$PWD/.venv/bin:$PATH"
exec .venv/bin/python -B scripts/run_demo.py --open "$@"
