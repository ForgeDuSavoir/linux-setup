#!/usr/bin/env bash

set -euo pipefail

if (($# != 1)); then
    echo "Usage: $(basename "$0") <manifest.json>" >&2
    exit 1
fi

manifest="$1"
manifest_directory="$(dirname -- "$manifest")"

if [[ ! -f "$manifest" ]]; then
    echo "Conversation manifest not found: $manifest" >&2
    exit 1
fi

cleanup() {
    rm -f -- "$manifest"
    rmdir -- "$manifest_directory" 2>/dev/null || true
}
trap cleanup EXIT

for command in node fzf; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "Required command not found: $command" >&2
        exit 1
    fi
done

selected="$({
    node -e '
const fs = require("node:fs");
const manifest = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
for (const element of manifest.elements ?? []) {
  const type = element.kind === "code" ? "code" : element.provenance ?? "link";
  const value = element.kind === "code" ? element.label : `${element.label} · ${element.uri}`;
  process.stdout.write(`${element.id}\t${type}\t${value.replace(/[\r\n\t]+/g, " ")}\n`);
}
' "$manifest" | fzf --delimiter=$'\t' --with-nth=2.. --prompt='Conversation > '
} || true)"

[[ -n "$selected" ]] || exit 0
id="${selected%%$'\t'*}"

kind="$(node -e '
const fs = require("node:fs");
const manifest = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
const element = (manifest.elements ?? []).find((item) => item.id === process.argv[2]);
if (!element) process.exit(2);
process.stdout.write(element.kind);
' "$manifest" "$id")"

case "$kind" in
    link)
        command -v xdg-open >/dev/null 2>&1 || {
            echo "Required command not found: xdg-open" >&2
            exit 1
        }
        uri="$(node -e '
const fs = require("node:fs");
const manifest = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
const element = (manifest.elements ?? []).find((item) => item.id === process.argv[2] && item.kind === "link");
if (!element) process.exit(2);
process.stdout.write(element.uri);
' "$manifest" "$id")"
        if command -v setsid >/dev/null 2>&1; then
            setsid -f xdg-open "$uri" </dev/null >/dev/null 2>&1
        else
            nohup xdg-open "$uri" </dev/null >/dev/null 2>&1 &
        fi
        ;;
    code)
        command -v wl-copy >/dev/null 2>&1 || {
            echo "Required command not found: wl-copy" >&2
            exit 1
        }
        node -e '
const fs = require("node:fs");
const manifest = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
const element = (manifest.elements ?? []).find((item) => item.id === process.argv[2] && item.kind === "code");
if (!element) process.exit(2);
process.stdout.write(element.content);
' "$manifest" "$id" | wl-copy
        echo "Extrait copié dans le presse-papiers."
        ;;
    *)
        echo "Unknown conversation element type: $kind" >&2
        exit 1
        ;;
esac
