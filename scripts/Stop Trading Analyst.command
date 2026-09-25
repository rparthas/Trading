#!/bin/bash
# Double-click to stop the Streamlit app if it is still running.

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1

stopped=0

if pkill -f "streamlit run app.py" 2>/dev/null; then
  stopped=1
fi

# Fallback: anything listening on Streamlit's default port
if command -v lsof >/dev/null 2>&1; then
  pids=$(lsof -ti tcp:8501 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    kill $pids 2>/dev/null && stopped=1
  fi
fi

echo ""
if [[ "$stopped" -eq 1 ]]; then
  echo "Trading Analyst stopped."
else
  echo "Trading Analyst was not running (or already closed)."
fi
echo ""
echo "Press Enter to close this window."
read -r _
