#!/usr/bin/env bash
echo "==============================================================="
echo "   HyperOS GlobalConvert - System Apps APK Patcher"
echo "   Repository: https://github.com/mertcqnkld/HyperOS-GlobalConvert"
echo "==============================================================="
echo ""
echo "[1] Start Modern Web UI (Browser based)"
echo "[2] Start CLI Interface (Console based)"
echo "[3] Push to GitHub"
echo ""
read -p "Select an option (1-3, Default: 1): " choice

if [ "$choice" == "2" ]; then
    python3 main.py
elif [ "$choice" == "3" ]; then
    python3 scripts/github_push.py
else
    echo "Starting Web UI on http://localhost:8080 ..."
    if which xdg-open > /dev/null; then
        xdg-open http://localhost:8080 &
    elif which open > /dev/null; then
        open http://localhost:8080 &
    fi
    python3 web/app.py 8080
fi
