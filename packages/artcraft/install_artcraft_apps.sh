#!/usr/bin/env bash

set -euo pipefail

# Install the 13 official Arch packages already archived by sync-artcraft-releases.
ARCHIVE_DIR="${ARTCRAFT_RELEASES_DIR:-${HOME}/Obsidian/Agora/3 Data/Resources/Artcraft/releases}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# The installed command and the repo entry point share the same app list.
APPS_FILE="${SCRIPT_DIR}/artcraft-apps.list"
if [[ ! -f "$APPS_FILE" ]]; then
    APPS_FILE="${SCRIPT_DIR}/../../scripts/artcraft-release-sync/artcraft-apps.list"
fi
if [[ ! -f "$APPS_FILE" ]]; then
    echo "✗ Missing ArtCraft app list: $APPS_FILE" >&2
    exit 1
fi
mapfile -t APPS < "$APPS_FILE"
if (( ${#APPS[@]} != 13 )); then
    echo "✗ Expected 13 ArtCraft apps in $APPS_FILE" >&2
    exit 1
fi

if [[ $# -gt 1 || ( $# -eq 1 && "$1" != "--check" ) ]]; then
    echo "Usage: $0 [--check]" >&2
    exit 2
fi

for tool in bsdtar pacman sha256sum awk vercmp; do
    if ! command -v "$tool" >/dev/null 2>&1; then
        echo "✗ Required command missing: $tool" >&2
        exit 1
    fi
done

packages=()
for app in "${APPS[@]}"; do
    dir="${ARCHIVE_DIR}/${app}/current"
    # The archive has packages for multiple architectures; match the entire suffix.
    matches=("${dir}/${app}"-*-linux-x86_64.pkg.tar.zst)
    if (( ${#matches[@]} != 1 )) || [[ ! -f "${matches[0]}" ]]; then
        echo "✗ ${app}: expected exactly one x86_64 Arch package in ${dir}" >&2
        exit 1
    fi
    pkg="${matches[0]}"
    checksums="${dir}/SHA256SUMS.txt"
    if [[ ! -f "$checksums" ]]; then
        echo "✗ ${app}: SHA256SUMS.txt is missing" >&2
        exit 1
    fi
    expected=$(awk -v file="${pkg##*/}" '$2 == file || $2 == "*" file {print $1}' "$checksums")
    if [[ ! "$expected" =~ ^[0-9a-fA-F]{64}$ ]]; then
        echo "✗ ${app}: missing or ambiguous checksum for ${pkg##*/}" >&2
        exit 1
    fi
    actual=$(sha256sum -- "$pkg")
    if [[ "${actual%% *}" != "$expected" ]]; then
        echo "✗ ${app}: SHA256 mismatch" >&2
        exit 1
    fi
    info=$(bsdtar -xOf "$pkg" .PKGINFO)
    name=$(awk '$1 == "pkgname" {print $3}' <<< "$info")
    version=$(awk '$1 == "pkgver" {print $3}' <<< "$info")
    if [[ "$name" != "ai.storyteller.${app}" || -z "$version" || "$pkg" != "${dir}/${app}-${version%-*}-linux-x86_64.pkg.tar.zst" ]]; then
        echo "✗ ${app}: unexpected package identity/version" >&2
        exit 1
    fi
    if installed=$(pacman -Q "$name" 2>/dev/null); then
        current=${installed#* }
        case $(vercmp "$current" "$version") in
            0) echo "✓ ${app} ${version} already installed"; continue ;;
            1) echo "✗ ${app}: installed version ${current} is newer than archive ${version}; refusing downgrade" >&2; exit 1 ;;
        esac
    fi
    echo "==> ${app}: ${version} verified, ready to install"
    packages+=("$pkg")
done

if (( ${#packages[@]} == 0 )); then
    echo "✓ All 13 ArtCraft applications are up to date."
elif [[ "${1:-}" == "--check" ]]; then
    printf '✓ Preflight passed: %s packages to install/update (no changes made).\n' "${#packages[@]}"
else
    # One transaction for the suite: pacman handles dependency and file conflict checks.
    sudo pacman -U -- "${packages[@]}"
    echo "✓ ArtCraft package installation complete."
fi
