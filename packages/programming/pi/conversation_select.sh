#!/usr/bin/env bash

set -euo pipefail

if (($# != 1)); then
    echo "Usage: $(basename "$0") <manifest.json>" >&2
    exit 1
fi

manifest="$1"
manifest_directory="$(dirname -- "$manifest")"
index_file="${manifest_directory}/row-index.json"
theme_file="${HOME}/.config/rofi/conversation-navigation.rasi"

if [[ ! -f "$manifest" ]]; then
    echo "Conversation manifest not found: $manifest" >&2
    exit 1
fi

cleanup() {
    rm -f -- "$index_file" "$manifest"
    rmdir -- "$manifest_directory" 2>/dev/null || true
}
trap cleanup EXIT

for command in node rofi; do
    if ! command -v "$command" >/dev/null 2>&1; then
        echo "Required command not found: $command" >&2
        exit 1
    fi
done

if [[ ! -f "$theme_file" ]]; then
    echo "Rofi theme not found: $theme_file" >&2
    exit 1
fi

set +e
selected_index="$({
    node - "$manifest" "$index_file" <<'NODE'
const fs = require("node:fs");
const manifestPath = process.argv[2];
const indexPath = process.argv[3];
const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
const rowIndex = [];

const plain = (value) => String(value ?? "").replace(/[\r\n\t]+/g, " ").replace(/\s+/g, " ").trim();
const markup = (value) => plain(value)
  .replaceAll("&", "&amp;")
  .replaceAll("<", "&lt;")
  .replaceAll(">", "&gt;")
  .replaceAll('"', "&quot;")
  .replaceAll("'", "&apos;");
const truncate = (value, max = 88) => value.length > max ? `${value.slice(0, max - 1)}…` : value;
const shortenUri = (uri) => {
  try {
    const parsed = new URL(uri);
    if (parsed.protocol === "file:") {
      const segments = decodeURIComponent(parsed.pathname).split("/").filter(Boolean);
      return `…/${segments.slice(-3).join("/")}`;
    }
    const path = parsed.pathname.length > 40 ? `${parsed.pathname.slice(0, 37)}…` : parsed.pathname;
    return truncate(`${parsed.host}${path}${parsed.search}${parsed.hash}`);
  } catch {
    return truncate(uri);
  }
};
const emit = (display, id, options = {}) => {
  const metadata = [];
  if (options.nonselectable) metadata.push("nonselectable\x1ftrue");
  if (options.meta) metadata.push(`meta\x1f${plain(options.meta)}`);
  process.stdout.write(display);
  if (metadata.length > 0) process.stdout.write(`\0${metadata.join("\x1f")}`);
  process.stdout.write("\n");
  rowIndex.push(id ?? null);
};

const grouped = new Map();
for (const element of manifest.elements ?? []) {
  const key = element.timestamp ?? 0;
  const group = grouped.get(key) ?? [];
  group.push(element);
  grouped.set(key, group);
}

for (const [timestamp, elements] of [...grouped.entries()].sort(([a], [b]) => a - b)) {
  const date = new Date(timestamp);
  const dateLabel = Number.isFinite(date.getTime())
    ? date.toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" }).replace(",", " —")
    : "message inconnu";
  const groupSearch = elements.map((element) => element.kind === "code"
    ? `${element.language ?? "texte"} ${element.content}`
    : `${element.label} ${element.uri}`).join(" ");
  emit(`<span foreground="#9aa5b5">──────── ${markup(dateLabel)} ────────</span>`, null, {
    nonselectable: true,
    meta: groupSearch,
  });

  for (const element of elements) {
    if (element.kind === "link") {
      const label = markup(element.label || element.uri);
      const target = markup(shortenUri(element.uri));
      emit(`<b>• ${label}</b> <span foreground="#9aa5b5">${target}</span>`, element.id, {
        meta: `${element.label} ${element.uri} ${element.provenance ?? "lien"}`,
      });
      continue;
    }

    const lines = String(element.content ?? "").split("\n");
    if (lines.at(-1) === "") lines.pop();
    const language = markup(element.language ?? "texte");
    const firstLine = lines.shift() ?? "(vide)";
    emit(`<b>• ${language}</b>  ${markup(firstLine)}`, element.id, {
      meta: `${element.language ?? "texte"} ${element.content}`,
    });
    for (const line of lines) {
      emit(`    <span foreground="#c7ccd4">${markup(line || " ")}</span>`, null, {
        nonselectable: true,
        meta: `${element.language ?? "texte"} ${element.content}`,
      });
    }
  }
}

fs.writeFileSync(indexPath, JSON.stringify(rowIndex), { mode: 0o600 });
NODE
} | rofi -dmenu -i -no-custom -markup-rows -format i -p 'Conversation' -theme "$theme_file")"
rofi_status=$?
set -e

if ((rofi_status != 0)) || [[ ! "$selected_index" =~ ^[0-9]+$ ]]; then
    exit 0
fi

id="$(node -e '
const fs = require("node:fs");
const index = JSON.parse(fs.readFileSync(process.argv[1], "utf8"));
const id = index[Number(process.argv[2])];
if (typeof id !== "string") process.exit(2);
process.stdout.write(id);
' "$index_file" "$selected_index")"

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
        ;;
    *)
        echo "Unknown conversation element type: $kind" >&2
        exit 1
        ;;
esac
