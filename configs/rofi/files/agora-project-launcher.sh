#!/usr/bin/env bash

set -euo pipefail

agora_root="${HOME}/Obsidian/Agora"
projects_root="${agora_root}/2 Projects"
default_terminal_launcher="${HOME}/.local/bin/launch-terminal-command"
theme_file="${HOME}/.config/rofi/project-launcher.rasi"
separator="────────────────────────"

if [[ ! -d "${agora_root}" ]]; then
    printf 'Agora directory not found: %s\n' "${agora_root}" >&2
    exit 1
fi

if [[ ! -x "${default_terminal_launcher}" ]]; then
    printf 'Default terminal launcher not found: %s\n' "${default_terminal_launcher}" >&2
    exit 1
fi

project_paths=()
if [[ -d "${projects_root}" ]]; then
    while IFS= read -r -d '' project_path; do
        project_paths+=("${project_path}")
    done < <(find "${projects_root}" -mindepth 1 -maxdepth 1 -type d -print0)

    if ((${#project_paths[@]} > 1)); then
        mapfile -d '' -t project_paths < <(printf '%s\0' "${project_paths[@]}" | LC_ALL=C sort -z)
    fi
else
    printf 'Projects directory not found: %s\n' "${projects_root}" >&2
fi

paths=("${agora_root}" "${project_paths[@]}")

menu_input() {
    printf '%s\n' 'Agora'
    printf '%s\0nonselectable\x1ftrue\n' "${separator}"

    local project_path project_name display_name
    for project_path in "${project_paths[@]}"; do
        project_name="${project_path##*/}"
        display_name="${project_name//$'\n'/↵}"
        printf '%s\n' "${display_name}"
    done
}

set +e
selected_index="$(menu_input | rofi -dmenu -i -no-custom -format i -p '' \
    -theme "${theme_file}" \
    -kb-accept-entry 'Return' \
    -kb-custom-1 'Control+Return' \
    -kb-custom-2 'Shift+Return' \
    -kb-cancel 'Escape,Super+p')"
rofi_status=$?
set -e

case "${rofi_status}" in
    0)
        open_yazi=true
        open_pi=true
        ;;
    10)
        open_yazi=false
        open_pi=true
        ;;
    11)
        open_yazi=true
        open_pi=false
        ;;
    *)
        exit 0
        ;;
esac

if [[ ! "${selected_index}" =~ ^[0-9]+$ ]]; then
    exit 0
fi

# Rofi indexes the separator as row 1; project rows start at 2.
if ((selected_index == 0)); then
    selected_path="${paths[0]}"
elif ((selected_index >= 2 && selected_index - 1 < ${#paths[@]})); then
    selected_path="${paths[selected_index - 1]}"
else
    exit 0
fi

if [[ "${open_yazi}" == true ]]; then
    "${default_terminal_launcher}" "${selected_path}" yazi &
fi

if [[ "${open_pi}" == true ]]; then
    if [[ -f "${selected_path}/AGENTS.md" ]]; then
        pi_path="${selected_path}"
    else
        pi_path="${agora_root}"
    fi

    "${default_terminal_launcher}" "${pi_path}" pi &
fi
