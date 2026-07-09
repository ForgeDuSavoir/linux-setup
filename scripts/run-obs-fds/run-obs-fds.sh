#!/usr/bin/env bash

set -euo pipefail

find_c922_device() {
    v4l2-ctl --list-devices | awk '
        /^C922 Pro Stream Webcam/ { found = 1; next }
        found && /^\t\/dev\/video/ { print $1; exit }
        found && /^[^[:space:]]/ { found = 0 }
    '
}

if ! command -v v4l2-ctl >/dev/null 2>&1; then
    echo "✗ v4l2-ctl is required to configure the Logitech webcam."
    echo "  Install v4l-utils first."
    exit 1
fi

WEBCAM_DEVICE="${WEBCAM_DEVICE:-$(find_c922_device)}"

if [[ -z "${WEBCAM_DEVICE}" ]]; then
    echo "✗ Logitech C922 Pro Stream Webcam not found."
    echo "  Connect the webcam or set WEBCAM_DEVICE=/dev/videoX."
    exit 1
fi

echo "==> Configuring Logitech C922 webcam (${WEBCAM_DEVICE})..."

v4l2-ctl -d "${WEBCAM_DEVICE}" -c auto_exposure=1
v4l2-ctl -d "${WEBCAM_DEVICE}" -c exposure_dynamic_framerate=0
v4l2-ctl -d "${WEBCAM_DEVICE}" -c exposure_time_absolute=220
v4l2-ctl -d "${WEBCAM_DEVICE}" -c gain=35
v4l2-ctl -d "${WEBCAM_DEVICE}" -c white_balance_automatic=0
v4l2-ctl -d "${WEBCAM_DEVICE}" -c white_balance_temperature=4700
v4l2-ctl -d "${WEBCAM_DEVICE}" -c focus_automatic_continuous=0
v4l2-ctl -d "${WEBCAM_DEVICE}" -c focus_absolute=0
v4l2-ctl -d "${WEBCAM_DEVICE}" -c brightness=132
v4l2-ctl -d "${WEBCAM_DEVICE}" -c contrast=115
v4l2-ctl -d "${WEBCAM_DEVICE}" -c saturation=135
v4l2-ctl -d "${WEBCAM_DEVICE}" -c sharpness=140
v4l2-ctl -d "${WEBCAM_DEVICE}" -c backlight_compensation=0
v4l2-ctl -d "${WEBCAM_DEVICE}" -c power_line_frequency=1

echo "==> Launching OBS..."

obs \
    --collection "Forge du Savoir" \
    >/dev/null 2>&1 &
