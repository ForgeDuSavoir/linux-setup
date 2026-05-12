#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$SCRIPT_DIR/pdf-arranger/install_pdf-arranger.sh"
"$SCRIPT_DIR/qalculate-gtk/install_qalculate-gtk.sh"
"$SCRIPT_DIR/printing/install_printing.sh"
