#!/usr/bin/env bash
# Only the physical sleep key; explicit suspend from menus remains available.
set -euo pipefail
if [[ $EUID != 0 ]]; then
    echo 'Run with sudo: bash configs/logind/configure_logind.sh --sleep-key-only' >&2
    exit 1
fi
target=/etc/systemd/logind.conf.d/agora-sleep-key.conf
[[ ! -L "$target" && ! -L /etc/systemd/logind.conf.d ]] || { echo 'Symlinked logind target refused.' >&2; exit 1; }
tmp="$(mktemp)";trap 'rm -f -- "$tmp"' EXIT
printf '[Login]\nHandleSuspendKey=ignore\nHandleSuspendKeyLongPress=ignore\n' > "$tmp"
install -d -m 755 /etc/systemd/logind.conf.d
if [[ ! -f "$target" ]] || ! cmp -s "$tmp" "$target"; then
    backup="$(mktemp -d /var/tmp/agora-sleep-key-backup-XXXXXXXX)";chmod 700 "$backup"
    if [[ -e "$target" ]]; then cp -p -- "$target" "$backup/prior.conf";fi
    install -m 644 "$tmp" "$target"
    echo "Private logind backup: $backup"
fi
# Reload is supported here; never restart logind or disturb the graphical session.
systemctl reload systemd-logind.service
for property in HandleSuspendKey HandleSuspendKeyLongPress; do
    [[ "$(busctl get-property org.freedesktop.login1 /org/freedesktop/login1 org.freedesktop.login1.Manager "$property")" == 's "ignore"' ]] || { echo "Effective $property is not ignore; inspect other logind drop-ins." >&2;exit 1; }
done
echo 'Sleep key ignored by logind. Run hyprctl reload as the graphical user to enable XF86Sleep control center.'
