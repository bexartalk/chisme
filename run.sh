#!/usr/bin/env bash
# Start (or restart) Chisme in the background. Usage: ./run.sh [port]
set -e
cd "$(dirname "$0")"
PORT="${1:-${PORT:-8211}}"
if [ ! -d venv ]; then python3 -m venv venv && ./venv/bin/pip install -q -r requirements.txt; fi
if [ -f server.pid ] && kill -0 "$(cat server.pid)" 2>/dev/null; then kill "$(cat server.pid)"; sleep 1; fi
nohup setsid ./venv/bin/uvicorn app:app --host 0.0.0.0 --port "$PORT" > server.log 2>&1 < /dev/null &
echo $! > server.pid
echo "Chisme running on http://localhost:$PORT (pid $(cat server.pid), log: server.log)"
