#!/usr/bin/env python3
"""Corrige l'import FilmCraft d'un OBS MKV à deux flux audio stéréo.

Usage: filmcraft-patch-desktop-audio recording.mkv premontage.fcproj
Audio 1-2 = premier flux (micro), Audio 3 = second flux stéréo (bureau),
Audio 4 = ancien canal erroné, supprimé. Préserve les coupes/source_in.
À utiliser sur un projet neuf, jamais sur un projet ouvert dans FilmCraft.
"""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def fail(message):
    raise RuntimeError(message)


def command(*args, input_text=None):
    proc = subprocess.run(args, input=input_text, text=True, capture_output=True)
    if proc.returncode:
        fail(f"Commande échouée : {' '.join(map(str, args))}\n{proc.stderr}\n{proc.stdout}")
    return proc.stdout


def fc(project, *args, input_text=None):
    return command("filmcraft-cli", "--project", str(project), *args, input_text=input_text)


def inspect(project):
    return json.loads(fc(project, "inspect", "sequence"))


def signature(clip):
    return tuple(clip[key] for key in ("clip", "start", "duration", "sourceIn", "link"))


def main():
    if len(sys.argv) != 3:
        fail("Usage : filmcraft-patch-desktop-audio recording.mkv premontage.fcproj")
    source, project = (Path(arg).resolve() for arg in sys.argv[1:])
    if not source.is_file() or not project.is_file():
        fail("Enregistrement ou projet FilmCraft introuvable")
    if source.parent != project.parent:
        fail("L'enregistrement et le projet doivent se trouver dans le même dossier")

    streams = json.loads(command("ffprobe", "-v", "error", "-select_streams", "a",
                                 "-show_entries", "stream=channels", "-of", "json", str(source)))["streams"]
    if len(streams) != 2 or any(s.get("channels") != 2 for s in streams):
        fail("Attendu : exactement deux flux audio stéréo (micro puis bureau). Aucun patch appliqué.")

    before = inspect(project)
    tracks = before.get("audio", [])
    if len(tracks) != 4 or not before.get("video") or not tracks[2]["items"]:
        fail("Attendu : quatre pistes audio non vides dans la séquence FilmCraft")
    if any(len(track["items"]) != len(tracks[2]["items"]) for track in tracks):
        fail("Les quatre pistes n'ont pas le même nombre de clips")
    for group in zip(*(track["items"] for track in tracks)):
        if any((c["start"], c["duration"], c["sourceIn"], c["item"]) !=
               (group[0]["start"], group[0]["duration"], group[0]["sourceIn"], group[0]["item"])
               for c in group[1:]):
            fail("Les pistes audio ne sont pas alignées ; patch refusé")
    # L'XML du flux pre-edit place les canaux 0,1,2,3 sur Audio 1,2,3,4.
    raw = json.loads(project.read_text())
    media_id = str(tracks[2]["items"][0]["item"])
    media_path = raw["project"]["items"][media_id]["kind"]["Media"]["media"]["File"]["path"]
    if (project.parent / media_path).resolve() != source:
        fail("Le média utilisé par Audio 3 n'est pas l'enregistrement fourni")
    sequences = [it["kind"]["Sequence"] for it in raw["project"]["items"].values()
                 if "Sequence" in it["kind"]]
    if (len(sequences) != 1 or [t["name"] for t in sequences[0]["audio_tracks"]] !=
            ["Audio 1", "Audio 2", "Audio 3", "Audio 4"]):
        fail("Structure du projet inattendue ; patch refusé")
    for channel, track in enumerate(sequences[0]["audio_tracks"]):
        if any(c.get("source_channels") != [channel] for c in track["items"]):
            fail(f"Canaux inattendus sur {track['name']} ; patch refusé")

    wav = project.with_name(source.stem + "_bureau.wav")
    if wav.exists():
        fail(f"Fichier déjà présent : {wav} (ne sera pas écrasé)")
    tmp_wav = None
    tmp_project = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".filmcraft-bureau-", suffix=".wav", dir=project.parent, delete=False) as f:
            tmp_wav = Path(f.name)
        # 0:a:1 = deuxième flux audio OBS, et NON deuxième canal du premier flux.
        command("ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
                "-map", "0:a:1", "-vn", "-c:a", "pcm_s16le", str(tmp_wav))
        if tmp_wav.stat().st_size < 1000:
            fail("Extraction du flux bureau vide")
        os.replace(tmp_wav, wav)
        tmp_wav = None

        with tempfile.NamedTemporaryFile(prefix=".filmcraft-patch-", suffix=".fcproj", dir=project.parent, delete=False) as f:
            tmp_project = Path(f.name)
        imported = json.loads(command("filmcraft-cli", "--project", str(project),
                                      "--save-as", str(tmp_project), "exec", "file.import",
                                      json.dumps({"paths": [str(wav)]})))
        tree = json.loads(fc(tmp_project, "inspect", "project"))
        matches = [it["item"] for it in tree["root"]["children"]
                   if it["name"] == wav.name and it["type"] == "Audio"]
        if len(matches) != 1:
            fail(f"Import de {wav.name} non confirmé : {imported}")
        audio_item = matches[0]

        # Un seul processus CLI : désactive la sélection liée pour ne PAS remplacer
        # aussi Audio 1-2 (le micro), puis rétablit cette préférence.
        steps = [
            {"id": "sequence.linkedSelection", "params": {"on": False}},
            {"id": "clip.replaceFromBin", "params": {
                "clips": [c["clip"] for c in tracks[2]["items"]],
                "item": audio_item, "keepSourceIn": True}},
            {"id": "sequence.deleteTrack", "params": {"track": tracks[3]["id"]}},
            {"id": "sequence.linkedSelection", "params": {"on": True}},
        ]
        output = fc(tmp_project, "--save", "run", "-",
                    input_text="".join(json.dumps(step) + "\n" for step in steps))
        results = [json.loads(line) for line in output.splitlines() if line.strip()]
        if len(results) != len(steps) or any(not row.get("ok") for row in results):
            fail(f"Résultat inattendu du patch : {output}")
        replacement = results[1]["result"]
        if (len(replacement.get("clips", [])) != len(tracks[2]["items"])
                or replacement.get("short") or replacement.get("sourceInClamped")):
            fail(f"Remplacement incomplet ou audio trop court : {replacement}")
        after = inspect(tmp_project)
        if (after["durationFrames"] != before["durationFrames"]
                or len(after["audio"]) != 3
                or any(t["id"] == tracks[3]["id"] for t in after["audio"])
                or after["video"] != before["video"]):
            fail("Durée, vidéo ou pistes audio incorrectes après suppression d'Audio 4")
        for index in range(3):
            old, new = tracks[index]["items"], after["audio"][index]["items"]
            if len(old) != len(new) or any(signature(a) != signature(b) for a, b in zip(old, new)):
                fail(f"Coupes modifiées sur Audio {index + 1}")
            expected = audio_item if index == 2 else None
            if any(b["item"] != (expected if expected is not None else a["item"])
                   for a, b in zip(old, new)):
                fail(f"Source incorrecte sur Audio {index + 1}")
        missing = json.loads(fc(tmp_project, "exec", "media.findMissing"))
        if missing.get("missing"):
            fail("Des médias manquent dans le projet patché")
        check = json.loads(tmp_project.read_text())
        patched = [it["kind"]["Sequence"] for it in check["project"]["items"].values()
                   if "Sequence" in it["kind"]][0]
        if (len(patched["audio_tracks"]) != 3
                or any(t["id"] == tracks[3]["id"] for t in patched["audio_tracks"])):
            fail("Audio 4 n'a pas été supprimée")
        os.replace(tmp_project, project)
        tmp_project = None
        print(f"✅ Son du bureau restauré sur Audio 3 : {len(tracks[2]['items'])} clips ; Audio 4 supprimée.")
        print(f"   WAV : {wav}")
        print(f"   Projet : {project}")
    finally:
        if tmp_wav is not None:
            tmp_wav.unlink(missing_ok=True)
        if tmp_project is not None:
            tmp_project.unlink(missing_ok=True)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, OSError, ValueError, KeyError, IndexError) as exc:
        print(f"❌ Patch audio FilmCraft : {exc}", file=sys.stderr)
        sys.exit(1)
