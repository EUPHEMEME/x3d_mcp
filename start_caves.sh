#!/usr/bin/env bash
# Serve the cave models locally and print the launcher URL.
cd "$(dirname "$0")" || exit 1
PORT="${1:-8099}"
echo ""
echo "  The Merriam Caves  ->  http://127.0.0.1:${PORT}/caves.html"
echo "  (Ctrl-C to stop)"
echo ""
exec python3 -m http.server "$PORT" --bind 127.0.0.1
