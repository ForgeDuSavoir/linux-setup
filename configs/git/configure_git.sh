#!/usr/bin/env bash

set -euo pipefail

SSH_DIR="${HOME}/.ssh"
PRIVATE_KEY="${SSH_DIR}/id_ed25519"
PUBLIC_KEY="${SSH_DIR}/id_ed25519.pub"
GITHUB_REMOTE="git@github.com:ForgeDuSavoir/linux-setup.git"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env"

if [[ -f "${ENV_FILE}" ]]; then
    source "${ENV_FILE}"
fi

ask_required_value() {
    local var_name="$1"
    local prompt="$2"
    local value="${!var_name:-}"

    if [[ -z "${value}" ]]; then
        read -r -p "${prompt}: " value
    fi

    if [[ -z "${value}" ]]; then
        echo "✗ ${var_name} cannot be empty."
        exit 1
    fi

    printf -v "$var_name" '%s' "$value"
}

echo "==> Configuring SSH key..."

mkdir -p "${SSH_DIR}"
chmod 700 "${SSH_DIR}"

if [[ ! -f "${PRIVATE_KEY}" || ! -f "${PUBLIC_KEY}" ]]; then
    echo "✗ No SSH key found in ${SSH_DIR}."

    read -r -p "Do you want to generate a new SSH key? [y/N]: " answer

    case "${answer}" in
        y|Y|yes|YES)
            ask_required_value EMAIL "Enter email for SSH key"
            ssh-keygen -t ed25519 -C "${EMAIL}" -f "${PRIVATE_KEY}" -N ""

            echo ""
            echo "✓ New SSH key generated."
            echo ""
            echo "Add this public key to GitHub:"
            echo "GitHub → Settings → SSH and GPG keys → New SSH key"
            echo ""
            cat "${PUBLIC_KEY}"
            echo ""

            read -r -p "Press Enter once you have added the key to GitHub..."
            ;;
        *)
            echo "✗ SSH key is required."
            echo "Copy your private/public key files to:"
            echo "  ${PRIVATE_KEY}"
            echo "  ${PUBLIC_KEY}"
            exit 1
            ;;
    esac
else
    echo "✓ SSH key found."
fi

echo "==> Fixing SSH permissions..."

chmod 700 "${SSH_DIR}"
chmod 600 "${PRIVATE_KEY}"
chmod 644 "${PUBLIC_KEY}"

echo "==> Starting SSH agent..."

if [[ -z "${SSH_AUTH_SOCK:-}" ]] || ! ssh-add -l >/dev/null 2>&1; then
    eval "$(ssh-agent -s)"
fi

if ! ssh-add -l 2>/dev/null | grep -q "$(ssh-keygen -lf "${PUBLIC_KEY}" | awk '{print $2}')"; then
    ssh-add "${PRIVATE_KEY}"
else
    echo "✓ SSH key already loaded."
fi

echo "==> Testing GitHub SSH connection..."

ssh -T git@github.com || true

echo "==> Setting Git remote to SSH..."
git remote set-url origin "${GITHUB_REMOTE}"

ask_required_value EMAIL "Enter git email"
ask_required_value USERNAME "Enter git username"

echo "==> Configuring git identity for this repo..."
git config user.name "${USERNAME}"
git config user.email "${EMAIL}"

echo "✓ SSH GitHub setup complete."