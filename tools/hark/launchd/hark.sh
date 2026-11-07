#!/bin/bash
# Install or remove Hark's login service (D8).
#   launchd/hark.sh install [module]   default module: hark.placeholder
#   launchd/hark.sh uninstall
#   launchd/hark.sh status
set -euo pipefail

LABEL=com.hark.agent
HERE="$(cd "$(dirname "$0")" && pwd)"
WORKDIR="$(dirname "$HERE")"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
LOGDIR="$HOME/Library/Logs/hark"
DOMAIN="gui/$(id -u)"

case "${1:-}" in
install)
    MODULE="${2:-hark.placeholder}"
    PYTHON="$WORKDIR/.venv/bin/python"
    [ -x "$PYTHON" ] || { echo "no $PYTHON: run 'uv sync' in $WORKDIR first" >&2; exit 1; }
    mkdir -p "$LOGDIR" "$(dirname "$PLIST")"
    sed -e "s|__PYTHON__|$PYTHON|" -e "s|__MODULE__|$MODULE|" \
        -e "s|__WORKDIR__|$WORKDIR|" -e "s|__LOGDIR__|$LOGDIR|" \
        "$HERE/$LABEL.plist.template" > "$PLIST"
    plutil -lint "$PLIST"
    launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
    launchctl bootstrap "$DOMAIN" "$PLIST"
    echo "installed $LABEL ($MODULE)"
    ;;
uninstall)
    launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
    rm -f "$PLIST"
    echo "removed $LABEL"
    ;;
status)
    launchctl print "$DOMAIN/$LABEL" | grep -E "state|pid|last exit" || echo "not loaded"
    ;;
*)
    echo "usage: $0 install [module] | uninstall | status" >&2
    exit 2
    ;;
esac
