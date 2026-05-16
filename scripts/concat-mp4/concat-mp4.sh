#!/bin/bash

# Vérifie qu'un argument est fourni
if [ -z "$1" ]; then
  echo "Usage: $0 /chemin/vers/dossier"
  exit 1
fi

DIR="$1"

# Vérifie que le dossier existe
if [ ! -d "$DIR" ]; then
  echo "Erreur : le dossier '$DIR' n'existe pas."
  exit 1
fi

# Fichier temporaire pour ffmpeg
LIST_FILE=$(mktemp)

# Trouve tous les mp4, tri alphabétique
find "$DIR" -maxdepth 1 -type f -iname "*.mp4" | sort | while read -r file; do
  echo "file '$file'" >> "$LIST_FILE"
done

# Vérifie qu'il y a au moins un fichier
if [ ! -s "$LIST_FILE" ]; then
  echo "Aucun fichier mp4 trouvé dans le dossier."
  rm "$LIST_FILE"
  exit 1
fi

OUTPUT="$DIR/merged.mp4"

echo "Concaténation en cours..."
ffmpeg -f concat -safe 0 -i "$LIST_FILE" -c copy "$OUTPUT"

# Nettoyage
rm "$LIST_FILE"

echo "Terminé : $OUTPUT"
