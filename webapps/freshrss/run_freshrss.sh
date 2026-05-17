#!/usr/bin/env bash

set -euo pipefail

PROFILE_PATH="__PROFILE_PATH__" URL="__FRESHRSS_URL__"
TAG="freshrss"

firefox --no-remote --profile "$PROFILE_PATH" --new-window "$URL" &
FIREFOX_PID=$!

echo "==> Waiting for Firefox window..."

for i in {1..50}; do
    ADDRESS="$(
        hyprctl clients -j |
        jq -r --arg title "FreshRSS" '
            .[]
            | select(.class == "firefox")
            | select(.title | test($title; "i"))
            | .address
        ' |
        head -n 1
    )"

    if [[ -n "$ADDRESS" ]]; then
        hyprctl dispatch tagwindow "+${TAG}" "address:${ADDRESS}"
        echo "✓ Tagged window ${ADDRESS} with ${TAG}"
        exit 0
    fi

    sleep 0.1
done

echo "✗ Could not find Firefox window to tag."
exit 1