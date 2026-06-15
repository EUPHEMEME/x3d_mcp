#!/usr/bin/env bash
# Serve the cave models on a local port and open the launcher in your browser.
# X_ITE loads the .x3d/textures over http, so the viewers need this server --
# double-clicking the .html files (file://) will not render.
cd "$(dirname "$0")" || exit 1
PORT="${1:-8099}"
URL="http://127.0.0.1:${PORT}/caves.html"

# open the browser once the server is up (background, after a short delay)
( for _ in 1 2 3 4 5 6 7 8 9 10; do
    if curl -s -o /dev/null "http://127.0.0.1:${PORT}/caves.html"; then break; fi
    sleep 0.3
  done
  if command -v open >/dev/null 2>&1; then open "$URL"
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL"; fi ) &

echo ""
echo "  The Merriam Caves  ->  ${URL}"
echo "  (Ctrl-C to stop the server)"
echo ""
exec python3 -m http.server "$PORT" --bind 127.0.0.1
