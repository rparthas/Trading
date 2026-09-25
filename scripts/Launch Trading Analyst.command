#!/bin/bash
# Double-click to start the Trading Analyst app (Streamlit).
# Optional: drag this file to the Desktop or Dock for quick access.

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1

pause_on_exit() {
  echo ""
  echo "Press Enter to close this window."
  read -r _
}

echo "Starting Trading Analyst…"
echo "Project: $ROOT"
echo ""

if [[ -f .env ]]; then
  set -a
  # shellcheck source=/dev/null
  source .env
  set +a
fi

if [[ ! -x .venv/bin/streamlit ]]; then
  echo "Dependencies are not installed yet. Running one-time setup (uv sync)…"
  if ! command -v uv >/dev/null 2>&1; then
    echo ""
    echo "Could not find 'uv'. Install it from https://docs.astral.sh/uv/getting-started/installation/"
    echo "Or ask whoever set up this Mac to run: uv sync --all-groups"
    pause_on_exit
    exit 1
  fi
  if ! uv sync --all-groups; then
    echo ""
    echo "Setup failed. Ask for help before trying again."
    pause_on_exit
    exit 1
  fi
fi

echo "Your browser should open automatically."
echo "To stop the app: close this window or run \"Stop Trading Analyst.command\"."
echo ""

if ! .venv/bin/streamlit run app.py; then
  echo ""
  echo "The app stopped with an error."
  pause_on_exit
  exit 1
fi

pause_on_exit
