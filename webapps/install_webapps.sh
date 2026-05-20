#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/chatgpt/install_chatgpt_webapp.sh"
"$SCRIPT_DIR/freshrss/install_freshrss_webapp.sh"
"$SCRIPT_DIR/syncthing/install_syncthing_webapp.sh"
"$SCRIPT_DIR/gmail/install_gmail_webapp.sh"
"$SCRIPT_DIR/gmail-pro/install_gmail-pro_webapp.sh"
"$SCRIPT_DIR/google-calendar/install_google-calendar_webapp.sh"
"$SCRIPT_DIR/youtube-qmk/install_youtube-qmk_webapp.sh"

echo
echo "✓ All webapps installed successfully."
