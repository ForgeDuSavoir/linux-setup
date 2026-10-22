#!/usr/bin/env bash

set -euo pipefail

ARCHIVE_DIR="${ARTCRAFT_RELEASES_DIR:-${HOME}/Obsidian/Agora/3 Data/Resources/Artcraft/releases}"
GITHUB_API_BASE_URL="https://api.github.com/repos/storytold"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
mapfile -t CRAFT_APPS < "${SCRIPT_DIR}/artcraft-apps.list"
if (( ${#CRAFT_APPS[@]} != 13 )); then
    echo "✗ Expected 13 ArtCraft apps in artcraft-apps.list." >&2
    exit 1
fi

require_command() {
    local command="$1"

    if ! command -v "${command}" >/dev/null 2>&1; then
        echo "✗ ${command} is required."
        exit 1
    fi
}

is_target_asset() {
    local filename="${1,,}"

    [[ "${filename}" == *linux* || "${filename}" == *windows* || "${filename}" == *macos* || "${filename}" == *universal* || "${filename}" == "sha256sums.txt" ]]
}

verify_checksums() {
    local release_dir="$1"
    local checksums_file="${release_dir}/SHA256SUMS.txt"
    local selected_checksums_file="${release_dir}/.selected-checksums"
    local checksum_line
    local filename

    if [[ ! -f "${checksums_file}" ]]; then
        echo "✗ No SHA256SUMS.txt asset was published; refusing unverified archives." >&2
        return 1
    fi

    while IFS= read -r checksum_line; do
        filename="${checksum_line#*  }"
        filename="${filename#\*}"

        if [[ -f "${release_dir}/${filename}" ]]; then
            printf '%s\n' "${checksum_line}" >> "${selected_checksums_file}"
        fi
    done < "${checksums_file}"

    if [[ ! -s "${selected_checksums_file}" ]]; then
        echo "✗ SHA256SUMS.txt has no checksum for the downloaded assets."
        return 1
    fi

    (
        cd "${release_dir}"
        sha256sum --check --status "$(basename "${selected_checksums_file}")"
    )

    rm -f "${selected_checksums_file}"
    echo "✓ Checksums verified."
}

sync_app() (
    local app="$1"
    local app_dir="${ARCHIVE_DIR}/${app}"
    local current_dir="${app_dir}/current"
    local staging_dir
    local release_json
    local tag_name
    local asset_name
    local asset_url
    local downloaded_assets=0
    local previous_dir

    mkdir -p "${app_dir}"
    staging_dir="$(mktemp -d "${app_dir}/.download.XXXXXX")"
    release_json="${staging_dir}/release.json"

    cleanup_staging() {
        rm -rf "${staging_dir}"
    }
    trap cleanup_staging EXIT

    echo "==> Checking ${app}..."
    curl --fail --silent --show-error --location --retry 3 \
        --header "Accept: application/vnd.github+json" \
        --header "User-Agent: linux-setup-artcraft-release-sync" \
        "${GITHUB_API_BASE_URL}/${app}/releases/latest" \
        --output "${release_json}"

    tag_name="$(jq --raw-output '.tag_name // empty' "${release_json}")"
    if [[ -z "${tag_name}" ]]; then
        echo "✗ ${app}: the latest release has no tag."
        return 1
    fi

    if [[ -f "${current_dir}/release.json" ]] \
        && [[ "$(jq --raw-output '.tag_name // empty' "${current_dir}/release.json")" == "${tag_name}" ]]; then
        echo "✓ ${app} ${tag_name} is already archived."
        return
    fi

    while IFS=$'\t' read -r asset_name asset_url; do
        if ! is_target_asset "${asset_name}"; then
            continue
        fi

        echo "  Downloading ${asset_name}..."
        curl --fail --silent --show-error --location --retry 3 \
            --header "User-Agent: linux-setup-artcraft-release-sync" \
            "${asset_url}" \
            --output "${staging_dir}/${asset_name}"
        ((downloaded_assets += 1))
    done < <(jq --raw-output '.assets[] | [.name, .browser_download_url] | @tsv' "${release_json}")

    if (( downloaded_assets == 0 )); then
        echo "✗ ${app} ${tag_name}: no Linux, Windows, macOS or checksum asset was found."
        return 1
    fi

    verify_checksums "${staging_dir}"

    previous_dir="${app_dir}/.previous-${tag_name}"
    rm -rf "${previous_dir}"

    if [[ -d "${current_dir}" ]]; then
        mv "${current_dir}" "${previous_dir}"
    fi

    if ! mv "${staging_dir}" "${current_dir}"; then
        if [[ -d "${previous_dir}" ]]; then
            mv "${previous_dir}" "${current_dir}"
        fi
        echo "✗ ${app} ${tag_name}: could not replace the previous archive."
        return 1
    fi

    rm -rf "${previous_dir}"
    echo "✓ ${app} ${tag_name} archived (${downloaded_assets} assets)."
)

require_command curl
require_command jq
require_command sha256sum

mkdir -p "${ARCHIVE_DIR}"

echo "==> Synchronizing ArtCraft Craft App Suite releases"
echo "Archive: ${ARCHIVE_DIR}"

for app in "${CRAFT_APPS[@]}"; do
    sync_app "${app}"
done

echo "✓ ArtCraft releases are up to date."
