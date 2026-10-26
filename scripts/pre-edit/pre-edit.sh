#!/usr/bin/env bash

set -euo pipefail

# -------- CONFIG --------
AUTOEDITOR="auto-editor"

# Piste utilisée pour la détection (ta voix dans OBS)
EDIT_EXPR='(audio:threshold=-34dB,stream=0)'

# Auto-Editor exporte aussi en XML Premiere (FCP 7), importable dans FilmCraft.
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
KDENLIVE_OUTPUT="${BASENAME}_premontage.kdenlive"
FILMCRAFT_XML="${BASENAME}_premontage.xml"
FILMCRAFT_PROJECT="${BASENAME}_premontage.fcproj"

notify() {
  if command -v notify-send >/dev/null 2>&1; then
    notify-send "$@" || true
  fi
}

filmcraft_failed() {
  echo "❌ FilmCraft : $1 (le projet Kdenlive reste disponible : $KDENLIVE_OUTPUT)" >&2
  notify "⚠️ Pré-montage FilmCraft échoué" "Kdenlive reste disponible : $KDENLIVE_OUTPUT"
  exit 1
}

echo "▶ Pré-montage en cours..."
echo "  Fichier   : $INPUT"
echo "  Kdenlive  : $KDENLIVE_OUTPUT"
echo "  FilmCraft : $FILMCRAFT_PROJECT"

# Préserver en priorité le projet Kdenlive pour pouvoir revenir au flux actuel.
if ! "$AUTOEDITOR" "$INPUT" \
  --edit "$EDIT_EXPR" \
  --margin 0.3s \
  --when-silent cut \
  --when-normal nil \
  --export kdenlive \
  -o "$KDENLIVE_OUTPUT" \
  --no-open; then
  notify "❌ Pré-montage échoué" "La génération Kdenlive a échoué : $INPUT"
  exit 1
fi

if ! command -v filmcraft-cli >/dev/null 2>&1 || ! command -v jq >/dev/null 2>&1; then
  filmcraft_failed "filmcraft-cli ou jq introuvable"
fi

if ! "$AUTOEDITOR" "$INPUT" \
  --edit "$EDIT_EXPR" \
  --margin 0.3s \
  --when-silent cut \
  --when-normal nil \
  --export premiere \
  -o "$FILMCRAFT_XML" \
  --no-open; then
  filmcraft_failed "export XML Premiere échoué"
fi

if [[ ! -s "$FILMCRAFT_XML" ]]; then
  filmcraft_failed "export XML Premiere absent ou vide"
fi

# L'XML référence la vidéo originale ; FilmCraft importe les coupes et sauvegarde un .fcproj.
IMPORT_PARAMS="$(jq -nc --arg path "$(realpath "$FILMCRAFT_XML")" '{paths:[$path]}')"
if ! IMPORT_RESULT="$(filmcraft-cli --save-as "$FILMCRAFT_PROJECT" exec file.import "$IMPORT_PARAMS")"; then
  filmcraft_failed "import XML échoué"
fi
if ! jq -e '(.errors | length) == 0 and (.sequences | length) > 0 and ([.documents[]?.offlineMedia[]?] | length) == 0' <<< "$IMPORT_RESULT" >/dev/null \
   || [[ ! -s "$FILMCRAFT_PROJECT" ]]; then
  echo "$IMPORT_RESULT" >&2
  filmcraft_failed "import incomplet (erreurs ou médias manquants)"
fi

# FilmCraft importe l'XML avec un chemin absolu. Relier à nouveau la vidéo par
# son nom, depuis le dossier du projet, pour enregistrer un chemin relatif.
SOURCE_NAME="$(basename "$INPUT")"
if [[ ! -f "$SOURCE_NAME" || "$(realpath "$INPUT")" != "$(realpath "$SOURCE_NAME")" ]]; then
  filmcraft_failed "la vidéo doit se trouver dans le même dossier que le projet FilmCraft"
fi
if ! MEDIA_ITEM="$(filmcraft-cli --project "$FILMCRAFT_PROJECT" inspect project \
  | jq -er '[.root.children[]? | select(.type == "Movie" or .type == "Audio") | .item] | if length == 1 then .[0] else empty end')"; then
  filmcraft_failed "impossible d'identifier l'unique média source à relier"
fi
RELINK_PARAMS="$(jq -nc --argjson item "$MEDIA_ITEM" --arg path "$SOURCE_NAME" '{item:$item,path:$path}')"
if ! RELINK_RESULT="$(filmcraft-cli --project "$FILMCRAFT_PROJECT" --save exec media.relink "$RELINK_PARAMS")"; then
  filmcraft_failed "liaison relative du média échouée"
fi
if ! jq -e --arg path "$SOURCE_NAME" '([.relinked[]? | select(.path == $path)] | length) == 1 and (.remaining | length) == 0' <<< "$RELINK_RESULT" >/dev/null \
   || ! filmcraft-cli --project "$FILMCRAFT_PROJECT" exec media.findMissing | jq -e '(.missing | length) == 0' >/dev/null; then
  filmcraft_failed "le projet FilmCraft contient encore un média introuvable"
fi

# OBS enregistre deux flux stéréo (micro, bureau). L'import XML peut faire
# rejouer le micro sur les pistes Audio 3-4 : restaurer le bureau sans perdre les coupes.
if ! command -v filmcraft-patch-desktop-audio >/dev/null 2>&1; then
  filmcraft_failed "filmcraft-patch-desktop-audio introuvable"
fi
if ! filmcraft-patch-desktop-audio "$INPUT" "$FILMCRAFT_PROJECT"; then
  filmcraft_failed "correctif du son du bureau échoué ; projet FilmCraft non patché"
fi

# Le nom d'export par défaut vient de la séquence, pas du nom du projet.
SEQUENCE_NAME="${BASENAME}_premontage"
SEQUENCE_PARAMS="$(jq -nc --arg name "$SEQUENCE_NAME" '{name:$name}')"
if ! filmcraft-cli --project "$FILMCRAFT_PROJECT" --save exec sequence.settings "$SEQUENCE_PARAMS" \
  || ! filmcraft-cli --project "$FILMCRAFT_PROJECT" inspect sequence \
    | jq -e --arg name "$SEQUENCE_NAME" '.name == $name' >/dev/null; then
  filmcraft_failed "renommage de la séquence FilmCraft échoué"
fi

echo "✅ Projets générés : $KDENLIVE_OUTPUT et $FILMCRAFT_PROJECT (audio corrigé)"
notify "🎬 Pré-montage terminé" "Kdenlive et FilmCraft : $BASENAME (audio corrigé)"
