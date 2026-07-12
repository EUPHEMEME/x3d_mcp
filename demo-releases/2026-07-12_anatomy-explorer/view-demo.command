#!/bin/sh
# The scene is a 10 MB .x3d and the page fetches two JSON files, so it must be
# served over HTTP -- opening the .html straight off disk trips CORS.
cd "$(dirname "$0")"
echo "LOA5 Anatomy Explorer -> http://localhost:8080/anatomy_explorer.html"
python3 -m http.server 8080 >/dev/null 2>&1 &
sleep 1
open "http://localhost:8080/anatomy_explorer.html" 2>/dev/null || \
  echo "open http://localhost:8080/anatomy_explorer.html"
wait
