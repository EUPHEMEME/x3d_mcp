#!/bin/bash
# Double-click this to view the demos in your browser.
# Browsers block X3D web players from reading local files directly (file://),
# so this serves the folder over a tiny local web server and opens the page.
cd "$(dirname "$0")"
PORT=8765
echo "Starting local demo server on http://localhost:$PORT ..."
python3 -m http.server $PORT >/dev/null 2>&1 &
SERVER=$!
sleep 1
open "http://localhost:$PORT/index.html"
echo
echo "  The demos are open in your browser."
echo "  Keep this window open while viewing."
echo "  Close it (or press Ctrl+C) when you're done to stop the server."
echo
trap "kill $SERVER 2>/dev/null" EXIT
wait $SERVER
