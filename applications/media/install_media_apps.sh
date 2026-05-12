#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/obs/install_obs.sh"
"$SCRIPT_DIR/kdenlive/install_kdenlive.sh"
"$SCRIPT_DIR/gimp/install_gimp.sh"
"$SCRIPT_DIR/auto-editor/install_auto-editor.sh"
"$SCRIPT_DIR/rembg/install_rembg.sh"
"$SCRIPT_DIR/v4l2loopback/install_v4l2loopback.sh"
"$SCRIPT_DIR/ffmpeg/install_ffmpeg.sh"
"$SCRIPT_DIR/hyprpicker/install_hyprpicker.sh"
"$SCRIPT_DIR/media-codecs/install_media-codecs.sh"
