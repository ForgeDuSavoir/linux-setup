#!/usr/bin/env bash

set -euo pipefail

REPO_PATH="."
COMMIT_MSG=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        -r|--repo)
            if [[ $# -lt 2 ]]; then
                echo "✗ Missing value for $1"
                exit 1
            fi

            REPO_PATH="$2"
            shift 2
            ;;
        -*)
            echo "✗ Unknown option: $1"
            exit 1
            ;;
        *)
            COMMIT_MSG="$1"
            shift
            ;;
    esac
done

if ! git -C "${REPO_PATH}" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo "✗ Not a git repository:"
    echo "  ${REPO_PATH}"
    exit 1
fi

cd "${REPO_PATH}"

echo "==> Pulling latest changes..."
git pull

echo "==> Staging changes..."
git add .

echo
echo "==> Staged changes:"
git status --short

echo

if [[ -z "${COMMIT_MSG}" ]]; then
    read -r -p "Enter commit message: " COMMIT_MSG
fi

if [[ -z "${COMMIT_MSG}" ]]; then
    echo "✗ Commit message cannot be empty."
    exit 1
fi

echo
echo "==> Creating commit..."
git commit -m "${COMMIT_MSG}"

echo
echo "==> Pushing changes..."
git push

echo
echo "✓ Git push completed successfully."