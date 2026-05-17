#!/usr/bin/env bash
#
# JAMES v2.0 — Tactical UI Launcher
# Starts both the Python API backend and the React frontend dev server.
#
# Usage:
#   ./launch_ui.sh          # Start both servers
#   ./launch_ui.sh --api    # API server only (port 8745)
#   ./launch_ui.sh --ui     # Frontend dev server only (port 5173)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB_DIR="$SCRIPT_DIR/web"
API_PORT="${JAMES_API_PORT:-8745}"
UI_PORT=5173

RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[0;33m'
BOLD='\033[1m'
RESET='\033[0m'

# Cleanup on exit
trap cleanup EXIT
PIDS=()

cleanup() {
    echo ""
    echo -e "${YELLOW}⚡ Shutting down JAMES services…${RESET}"
    for pid in "${PIDS[@]}"; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            wait "$pid" 2>/dev/null
        fi
    done
    echo -e "${GREEN}✓ All services stopped.${RESET}"
}

banner() {
    echo -e "${CYAN}${BOLD}"
    echo "     ╔══════════════════════════════════════╗"
    echo "     ║     ⚡ JAMES v2.0 — Tactical UI     ║"
    echo "     ║     Wi-Fi Pentesting Agent           ║"
    echo "     ╚══════════════════════════════════════╝"
    echo -e "${RESET}"
}

start_api() {
    echo -e "${CYAN}[API]${RESET} Starting backend on port ${BOLD}${API_PORT}${RESET}…"
    cd "$SCRIPT_DIR"
    python3 -m james.api.server &
    PIDS+=($!)
    echo -e "${GREEN}[API]${RESET} Backend PID: ${PIDS[-1]}"
}

start_ui() {
    echo -e "${CYAN}[UI]${RESET} Starting frontend dev server on port ${BOLD}${UI_PORT}${RESET}…"

    # Check if node_modules exist
    if [ ! -d "$WEB_DIR/node_modules" ]; then
        echo -e "${YELLOW}[UI]${RESET} Installing npm dependencies…"
        cd "$WEB_DIR" && npm install
    fi

    cd "$WEB_DIR"
    npx vite --host 0.0.0.0 --port "$UI_PORT" &
    PIDS+=($!)
    echo -e "${GREEN}[UI]${RESET} Frontend PID: ${PIDS[-1]}"
}

# ── Main ────────────────────────────────────────────────────────
banner

case "${1:-}" in
    --api)
        start_api
        ;;
    --ui)
        start_ui
        ;;
    *)
        start_api
        sleep 2
        start_ui
        echo ""
        echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
        echo -e "${GREEN}  ✓ JAMES Tactical UI is live!${RESET}"
        echo -e ""
        echo -e "  ${BOLD}Frontend:${RESET}  http://localhost:${UI_PORT}/"
        echo -e "  ${BOLD}API:${RESET}       http://localhost:${API_PORT}/"
        echo -e "  ${BOLD}WebSocket:${RESET} ws://localhost:${API_PORT}/ws"
        echo -e ""
        echo -e "  ${YELLOW}Press Ctrl+C to stop all services.${RESET}"
        echo -e "${GREEN}${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
        ;;
esac

# Wait for child processes
wait
