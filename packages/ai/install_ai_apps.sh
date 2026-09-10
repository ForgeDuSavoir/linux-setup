#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/ollama/install_ollama.sh"
"$SCRIPT_DIR/whisper-cpp/install_whisper-cpp.sh"
