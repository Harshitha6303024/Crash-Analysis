#!/usr/bin/env bash
# setup_kdump.sh - configure kdump/kexec so a crash produces a vmcore
# the analyzer can read.

set -euo pipefail

if [[ $EUID -ne 0 ]]; then
    echo "Run as root (sudo ./setup_kdump.sh)" >&2
    exit 1
fi

CRASHKERNEL_SIZE="${CRASHKERNEL_SIZE:-256M}"

echo "[*] Detecting distro..."
if command -v apt-get >/dev/null 2>&1; then
    DISTRO="debian"
elif command -v dnf >/dev/null 2>&1; then
    DISTRO="fedora"
else
    echo "Unsupported distro - install kdump-tools (Debian/Ubuntu) or" >&2
    echo "kexec-tools (Fedora/RHEL) manually, then reserve crash memory" >&2
    echo "via the crashkernel= kernel cmdline parameter." >&2
    exit 1
fi
echo "    -> $DISTRO"

# --- 1. Reserve memory for the crash kernel via crashkernel= ------------
GRUB_FILE="/etc/default/grub"
if [[ -f "$GRUB_FILE" ]] && ! grep -q "crashkernel=" "$GRUB_FILE"; then
    echo "[*] Adding crashkernel=${CRASHKERNEL_SIZE} to GRUB_CMDLINE_LINUX"
    cp "$GRUB_FILE" "${GRUB_FILE}.crashlab.bak"
    sed -i \
        "s/^GRUB_CMDLINE_LINUX=\"/GRUB_CMDLINE_LINUX=\"crashkernel=${CRASHKERNEL_SIZE} /" \
        "$GRUB_FILE"
    update-grub 2>/dev/null || grub2-mkconfig -o /boot/grub2/grub.cfg
    NEEDS_REBOOT=1
else
    echo "[*] crashkernel= already configured or GRUB file not found; skipping"
    NEEDS_REBOOT=0
fi

# --- 2. Install + enable the kdump service -------------------------------
if [[ "$DISTRO" == "debian" ]]; then
    echo "[*] Installing kdump-tools..."
    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y kdump-tools

    echo "[*] Enabling kdump-tools..."
    sed -i 's/^USE_KDUMP=.*/USE_KDUMP=1/' /etc/default/kdump-tools 2>/dev/null || \
        echo "USE_KDUMP=1" >> /etc/default/kdump-tools
    systemctl enable kdump-tools.service || true

elif [[ "$DISTRO" == "fedora" ]]; then
    echo "[*] Installing kexec-tools..."
    dnf install -y kexec-tools

    echo "[*] Enabling kdump.service..."
    systemctl enable kdump.service
fi

echo
if [[ "$NEEDS_REBOOT" -eq 1 ]]; then
    echo "[!] Reboot required to reserve crash-kernel memory:"
    echo "        sudo reboot"
    echo "    After rebooting, verify with:"
    echo "        cat /sys/kernel/kexec_crash_loaded   # should print 1"
else
    echo "[*] Verify kdump is active with:"
    echo "        cat /sys/kernel/kexec_crash_loaded   # should print 1"
fi
echo "[*] Crash dumps will be written under /var/crash/"
