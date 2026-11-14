#!/usr/bin/env bash
# Launch Firefox with a private, persistent profile selected by project identity.
set -euo pipefail

if [[ $# -lt 1 || ! "$1" =~ ^[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}$ ]]; then
    echo 'agora-project-firefox: expected a project profile UUID' >&2
    exit 2
fi
profile_id="$1"
shift

# Browser data stays outside Agora. The UUID is stored in the project's
# desktop entry so folder renames do not silently select another profile.
data_home="${XDG_DATA_HOME:-${HOME}/.local/share}"
if [[ "${data_home}" != /* ]]; then
    echo 'agora-project-firefox: XDG_DATA_HOME must be absolute' >&2
    exit 2
fi
root="${data_home}/agora-project-firefox"
profile="${root}/${profile_id}/firefox-profile"
if [[ -L "${root}" || -L "${root}/${profile_id}" || -L "${profile}" ]]; then
    echo 'agora-project-firefox: refusing a symlinked profile directory' >&2
    exit 1
fi
umask 077
install -d -m 0700 -- "${profile}"
exec firefox --no-remote --profile "${profile}" --new-window "$@"
