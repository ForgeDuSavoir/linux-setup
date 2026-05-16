#!/usr/bin/env bash

set -e

# -------- CONFIG --------
AUTOEDITOR="auto-editor"

# Piste utilisée pour la détection (ta voix dans OBS)
EDIT_EXPR='(audio:threshold=-34dB,stream=0)'

# Nom d'export Kdenlive (sans attributs avancés)
EXPORT_MODE="kdenlive"
# ------------------------

if [ $# -ne 1 ]; then
  echo "Usage: premontage.sh <video.mkv>"
  exit 1
fi

INPUT="$1"

if [ ! -f "$INPUT" ]; then
  echo "Erreur : fichier introuvable -> $INPUT"
  exit 1
fi

BASENAME="$(basename "$INPUT")"
BASENAME="${BASENAME%.*}"
OUTPUT="${BASENAME}_premontage.kdenlive"

echo "▶ Pré-montage en cours..."
echo "  Fichier : $INPUT"
echo "  Sortie  : $OUTPUT"

"$AUTOEDITOR" "$INPUT" \
  --edit "$EDIT_EXPR" \
  --margin 0.3s \
  --when-silent cut \
  --when-normal nil \
  --export "$EXPORT_MODE" \
  -o "$OUTPUT"

echo "✅ Terminé."
echo "👉 Ouvre '$OUTPUT' dans Kdenlive"

EC=$?   # juste après la commande auto-editor

if [ "${EC:-1}" -eq 0 ]; then
  notify-send "🎬 Pré-montage terminé" "$OUTPUT généré avec succès."
else
  notify-send "❌ Pré-montage échoué" "Vérifie le terminal."
fi

exit "$EC"
