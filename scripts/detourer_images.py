"""Détoure des photos produit (fond transparent) pour le carrousel de l'accueil.

Usage :
    pip install "rembg[cpu]" pillow
    python scripts/detourer_images.py dossier_photos/ static/img/hero/ [--model u2net]

Chaque .jpg/.png du dossier source devient un .webp carré 600x600 détouré.
Modèles utiles : isnet-general-use (défaut, net sur fond contrasté), u2net (meilleur
sur les consoles blanches).
"""

import argparse
import pathlib

from PIL import Image
from rembg import new_session, remove


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("src", type=pathlib.Path)
    parser.add_argument("dst", type=pathlib.Path)
    parser.add_argument("--model", default="isnet-general-use")
    args = parser.parse_args()

    args.dst.mkdir(parents=True, exist_ok=True)
    session = new_session(args.model)
    for f in sorted([*args.src.glob("*.jpg"), *args.src.glob("*.png")]):
        im = remove(Image.open(f).convert("RGB"), session=session)
        im = im.crop(im.getbbox())
        side = int(max(im.size) * 1.08)
        canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        canvas.paste(im, ((side - im.width) // 2, (side - im.height) // 2), im)
        canvas.resize((600, 600), Image.LANCZOS).save(args.dst / f"{f.stem}.webp", "WEBP", quality=88)
        print(f"{f.stem}.webp")


if __name__ == "__main__":
    main()
