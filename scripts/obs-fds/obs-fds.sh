#!/usr/bin/env bash

set -euo pipefail

echo "==> Starting virtual camera..."

if ! lsmod | grep -q v4l2loopback; then
    sudo modprobe v4l2loopback \
        devices=1 \
        video_nr=10 \
        card_label="AndroidCam" \
        exclusive_caps=1
fi

echo "==> Starting scrcpy camera..."

pkill -f "scrcpy.*--video-source=camera" || true

scrcpy \
    --video-source=camera \
    --camera-facing=back \
    --no-audio \
    --v4l2-sink=/dev/video10 \
    --no-playback \
    >/dev/null 2>&1 &

sleep 2

echo "==> Launching OBS..."

obs \
    --collection "Forge du Savoir" \
    >/dev/null 2>&1 &