# Stop Thunar first, otherwise some settings may not apply immediately
thunar -q 2>/dev/null || true

echo "==> Setting Thunar as default file manager..."

xdg-mime default thunar.desktop inode/directory
xdg-mime default thunar.desktop application/x-gnome-saved-search

echo "==> Applying Thunar preferences..."

# Location selector: button/pathbar style
xfconf-query -c thunar -p /last-location-bar -n -t string -s ThunarLocationButtons

# Expandable folders in list view
xfconf-query -c thunar -p /misc-expandable-folders -n -t bool -s true

echo "✓ Thunar preferences applied."

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"

SOURCE_UCA="${SCRIPT_DIR}/files/uca.xml"
TARGET_UCA_DIR="${HOME}/.config/Thunar"
TARGET_UCA="${TARGET_UCA_DIR}/uca.xml"

echo "==> Installing Thunar custom actions..."

mkdir -p "${TARGET_UCA_DIR}"

if [[ -f "${SOURCE_UCA}" ]]; then
    cp "${SOURCE_UCA}" "${TARGET_UCA}"
    echo "✓ Thunar custom actions installed."
else
    echo "⚠ No uca.xml found, skipping custom actions."
fi