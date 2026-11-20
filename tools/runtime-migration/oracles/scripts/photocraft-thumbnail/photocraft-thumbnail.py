#!/usr/bin/env python3
"""Build a 1920x1080 two-layer PhotoCraft thumbnail from a directory of images."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from zipfile import BadZipFile, ZipFile

FORMATS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}
OUTPUT_NAME = "miniature.pcraft"
MASK_TEMPLATE = Path(__file__).with_name("photocraft-thumbnail-mask.zip")
# Require both a sizeable absolute gap and at least 25% dimming in the central scene.
MIN_LUMA_GAP = 15
MAX_DARK_TO_BRIGHT = 0.75


def fail(message):
    raise SystemExit(f"photocraft-thumbnail: {message}")


def run(*args):
    try:
        return subprocess.run(args, check=True, text=True, capture_output=True).stdout
    except subprocess.CalledProcessError as exc:
        fail(f"{args[0]} a échoué : {exc.stderr.strip() or exc.stdout.strip()}")


def size(image):
    probe = json.loads(run("ffprobe", "-v", "error", "-select_streams", "v:0",
                           "-show_entries", "stream=width,height", "-of", "json", str(image)))
    streams = probe.get("streams", [])
    if len(streams) != 1:
        fail(f"Impossible de lire les dimensions de {image.name}")
    return streams[0]["width"], streams[0]["height"]


def prepare(image, target):
    width, height = size(image)
    if width * 10 != height * 16 or width < 1920 or width % 16:
        fail(f"{image.name} : attendu au moins 1920 px de large au format exact 16:10, obtenu {width}x{height}")
    crop_height = width * 9 // 16
    if crop_height > height or (height - crop_height) % 2:
        fail(f"{image.name} : recadrage 16:9 centré impossible avec des pixels entiers")
    top = (height - crop_height) // 2
    print(f"{image.name} : {width}x{height} → crop 0,{top},{width},{crop_height} → 1920x1080")
    run("ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
        "-i", str(image), "-vf",
        f"crop={width}:{crop_height}:0:{top},scale=1920:1080:flags=lanczos,format=rgba",
        "-frames:v", "1", str(target))


def brightness(image):
    # The central map remains visible in both screenshots. Sample it after the
    # crop/resize, excluding the leader on the left and the UI on the right.
    proc = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-i", str(image),
         "-vf", "crop=576:756:672:162,scale=32:32:flags=area,format=gray",
         "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
        capture_output=True, check=False,
    )
    if proc.returncode or len(proc.stdout) != 32 * 32:
        fail(f"Impossible de mesurer la luminosité de {image.name} : {proc.stderr.decode(errors='replace').strip()}")
    return sum(proc.stdout) / len(proc.stdout)


def apply_reference_mask(project, masked_project, top_name, bottom_name):
    """Copy the exact 1920x1080 U8 raster mask, never the reference's image pixels."""
    try:
        with ZipFile(MASK_TEMPLATE) as template, ZipFile(project) as source:
            reference = json.loads(template.read("mask.json"))
            document = json.loads(source.read("manifest.json"))
            if (reference["format_version"] != document["format_version"] or
                    (reference["width"], reference["height"]) != (1920, 1080) or
                    document["document"]["size"] != {"width": 1920, "height": 1080}):
                fail("Format du projet ou du masque incompatible (attendu : PhotoCraft v1, 1920x1080)")
            layers = document["document"]["layers"]  # PhotoCraft stores bottom -> top.
            if (len(layers) != 2 or layers[0]["name"] != bottom_name or
                    layers[1]["name"] != top_name or any(layer.get("mask") for layer in layers)):
                fail("Calques inattendus : impossible de poser le masque sur le dirigeant")
            mask = reference["mask"]
            tiles = mask["surface"]["tiles"]
            coords = {(tile["tx"], tile["ty"]) for tile in tiles}
            if (mask["surface"]["format"] != {"mode": "Grayscale", "sample": "U8", "alpha": False} or
                    len(tiles) != 40 or coords != {(x, y) for x in range(8) for y in range(5)}):
                fail("Masque de référence incomplet ou incompatible")
            tile_paths = set()
            for tile in tiles:
                if not re.fullmatch(r"[0-9a-f]{64}", tile["hash"]):
                    fail("Référence de tuile invalide dans le masque")
                tile_paths.add(f"tiles/{tile['hash']}.zst")
            layers[1]["mask"] = mask
            present = set(source.namelist())
            with ZipFile(masked_project, "w") as output:
                for item in source.infolist():
                    output.writestr(item, json.dumps(document).encode() if item.filename == "manifest.json"
                                    else source.read(item.filename))
                for path in sorted(tile_paths):
                    data = template.read(path)
                    if path in present:
                        if source.read(path) != data:
                            fail("Conflit de tuiles entre le projet et le masque")
                    else:
                        output.writestr(path, data)
    except (OSError, KeyError, TypeError, ValueError, BadZipFile) as exc:
        fail(f"Impossible d'appliquer le masque PhotoCraft : {exc}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", help="dossier contenant exactement deux images")
    parser.add_argument("--top", help="nom du fichier à placer au-dessus si la détection est incertaine")
    args = parser.parse_args()
    requested_dir = Path(args.directory).expanduser()
    if not requested_dir.is_dir():
        fail(f"Dossier introuvable : {requested_dir}")
    directory = requested_dir.resolve(strict=True)
    images = sorted((p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in FORMATS),
                    key=lambda p: (p.name.casefold(), p.name))
    if len(images) != 2:
        fail(f"Attendu : exactement deux images PNG/JPEG/WebP/TIFF/BMP dans {directory} ; trouvé {len(images)}")
    if any(p.is_symlink() for p in images):
        fail("Les images doivent être des fichiers réguliers, pas des liens symboliques")
    destination = directory / OUTPUT_NAME
    if destination.exists() or destination.is_symlink():
        fail(f"Le projet existe déjà, il ne sera pas écrasé : {destination}")

    with tempfile.TemporaryDirectory(prefix=".photocraft-thumbnail-", dir=directory) as temp_dir:
        temp = Path(temp_dir)
        prepared = {image: temp / f"{index}.png" for index, image in enumerate(images)}
        for image in images:
            prepare(image, prepared[image])
        scores = {image: brightness(prepared[image]) for image in images}
        print("Luminosité au centre : " + ", ".join(f"{image.name} = {scores[image]:.1f}" for image in images))
        if args.top:
            matches = [image for image in images if image.name == args.top]
            if len(matches) != 1:
                fail("--top doit être le nom exact d'une des deux images du dossier")
            top = matches[0]
        else:
            top = min(images, key=scores.get)
            bottom_candidate = max(images, key=scores.get)
            darker, lighter = scores[top], scores[bottom_candidate]
            if lighter - darker < MIN_LUMA_GAP or darker > lighter * MAX_DARK_TO_BRIGHT:
                fail("Différence de luminosité insuffisante pour choisir le dirigeant sans risque ; "
                     "relancer avec --top 'nom-exact-de-l-image.png'")
        bottom = next(image for image in images if image != top)
        project = temp / OUTPUT_NAME
        run("photocraft-cli", "run", str(prepared[bottom]),
            "--cmd", "layer.setProps", "--params", json.dumps({"name": bottom.name}),
            "--cmd", "file.placeEmbedded", "--params",
            json.dumps({"path": str(prepared[top]), "fit": False, "smartObject": False}),
            "--cmd", "layer.setProps", "--params", json.dumps({"name": top.name}),
            "--out", str(project))
        if not project.is_file() or not project.stat().st_size:
            fail("PhotoCraft n'a pas créé le projet")
        masked_project = temp / "masked.pcraft"
        apply_reference_mask(project, masked_project, top.name, bottom.name)
        info = json.loads(run("photocraft-cli", "info", str(masked_project), "--compact"))
        layers = info.get("layers", [])
        if (info.get("width"), info.get("height")) != (1920, 1080) or len(layers) != 2:
            fail("Le projet ne contient pas exactement deux calques en 1920x1080")
        for layer, image in zip(layers, (top, bottom)):
            if layer.get("name") != image.name or layer.get("bounds") != [0, 0, 1920, 1080]:
                fail("Les calques PhotoCraft ne correspondent pas aux images préparées")
        if not layers[0].get("hasMask") or layers[1].get("hasMask"):
            fail("Le masque n'est pas présent uniquement sur le calque supérieur")
        try:
            os.link(masked_project, destination)  # atomic no-overwrite; temp is on the same filesystem
        except FileExistsError:
            fail(f"Le projet a été créé entre-temps, il ne sera pas écrasé : {destination}")
    print(f"✓ Projet créé : {destination}")
    print(f"  En haut : {top.name} (masque et dégradé identiques au modèle) ; en bas : {bottom.name}")


if __name__ == "__main__":
    main()
