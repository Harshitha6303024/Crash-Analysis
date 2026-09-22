#!/usr/bin/env bash
# trigger_crash.sh - build crashlab.ko , load it, and trigger
# one specific bug.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULE_DIR="$SCRIPT_DIR/../kernel_modules"
DEBUGFS_DIR="/sys/kernel/debug/crashlab"

if [[ $EUID -ne 0 ]]; then
    echo "Run as root (sudo ./trigger_crash.sh <bug_name>)" >&2
    exit 1
fi

if [[ ! -d "$DEBUGFS_DIR" ]]; then
    echo "[*] crashlab not loaded yet - building and inserting module..."
    make -C "$MODULE_DIR"
    insmod "$MODULE_DIR/crashlab.ko"
    sleep 1
fi

if [[ $# -eq 0 ]]; then
    echo "Available bug names:"
    cat "$DEBUGFS_DIR/list"
    exit 0
fi

BUG_NAME="$1"

echo "[*] Available bugs:"
cat "$DEBUGFS_DIR/list"
echo
echo "[!] About to trigger: $BUG_NAME"
echo "[!] This VM may crash, hang, or reboot in the next few seconds."
read -r -p "    Type 'yes' to continue: " CONFIRM
if [[ "$CONFIRM" != "yes" ]]; then
    echo "Aborted."
    exit 1
fi

sync   # flush disk buffers first - we're about to (maybe) crash
echo "$BUG_NAME" > "$DEBUGFS_DIR/trigger"

echo "[*] Trigger written. If the machine is still up, check: dmesg | tail -30"
echo "[*] After reboot, look for a new vmcore under /var/crash/"
