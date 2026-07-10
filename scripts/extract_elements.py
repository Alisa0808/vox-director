#!/usr/bin/env python3
"""
Extract independent collage elements from a static card (the core of the
"motion collage" pipeline — animating 26 cut-out pieces, not one whole card).

Reads <project>/elements_spec.json:
  {"card": "<png>", "elements": [{"name","bbox":[x0,y0,x1,y1],"mode":"cutout|crop"}]}
 - crop : rectangle crop kept as-is (newspaper strips / text blocks)
 - cutout: crop -> youchuan remove-background -> transparent PNG (figures/trophies/stickers)

Saves elements/<name>.png (RGBA). Usage: python3 extract_elements.py <project_dir>
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

from provider import get_provider, run_jobs

RMBG = "youchuan/v8.1/remove-background"


def apply_erase(elem, bbox, erase):
    """Erase (feathered) sub-regions from a cut element, given in CARD coords.
    Used to remove an object that youchuan pulled in with the subject
    (e.g. a trophy embedded in the player cutout)."""
    import numpy as np
    ox, oy = bbox[0], bbox[1]
    mask = Image.new("L", elem.size, 255)
    d = ImageDraw.Draw(mask)
    for r in erase:
        d.rounded_rectangle([r[0] - ox, r[1] - oy, r[2] - ox, r[3] - oy], radius=30, fill=0)
    mask = mask.filter(ImageFilter.GaussianBlur(14))
    a = np.asarray(elem.split()[3], dtype=float) * (np.asarray(mask, dtype=float) / 255.0)
    elem.putalpha(Image.fromarray(a.astype("uint8"), "L"))
    return elem


def run(project_dir):
    spec = json.load(open(os.path.join(project_dir, "elements_spec.json")))
    card = Image.open(spec["card"]).convert("RGBA")
    ed = os.path.join(project_dir, "elements"); os.makedirs(ed, exist_ok=True)

    prov = get_provider(spec.get("provider"))
    for el in spec["elements"]:
        name, bbox, mode = el["name"], el["bbox"], el.get("mode", "crop")
        crop = card.crop(tuple(bbox))
        raw = os.path.join(ed, f"raw_{name}.png")
        crop.save(raw)
        out = os.path.join(ed, f"{name}.png")
        if mode == "cutout":
            url = prov.upload(raw)
            res = run_jobs(prov, {name: lambda u=url: prov.remove_bg(RMBG, u)},
                           poll_s=3, stall_s=60, max_retries=2, deadline_s=180)[name]
            if res:
                prov.download(res, out)
            elem = Image.open(out).convert("RGBA")
        else:
            elem = crop
        if el.get("erase"):
            elem = apply_erase(elem, bbox, el["erase"])
        elem.save(out)
        print(f"[{name}] {mode} -> {out}")
        el["file"] = out
        el["size"] = list(crop.size)

    json.dump(spec, open(os.path.join(project_dir, "elements_spec.json"), "w"),
              ensure_ascii=False, indent=2)
    print("done ->", ed)


if __name__ == "__main__":
    proj = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "out", "cr7-act")
    run(os.path.abspath(proj))
