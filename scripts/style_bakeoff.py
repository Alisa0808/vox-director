#!/usr/bin/env python3
"""
Style bake-off: render ONE representative beat in several candidate collage styles so
the user can pick the visual idiom before committing the whole film.

Hybrid selection: Claude reads the topic and chooses which idioms to try (names from
styles.STYLE_LIBRARY, or a custom idiom string), matching the topic's era/culture/tone —
don't default to Chinese motifs for a Western topic. Then the human picks by eye.

Usage:
  python3 style_bakeoff.py <project_dir> [style1,style2,...] [beat_index]
Defaults: the 4 Western library styles, beat 0. Output -> <project>/style-bakeoff/<style>.jpg
Then set  "collage_style": "<pick>"  in beats.json, clear old keyframe_url/path, re-run keyframes.
"""
import json
import os
import sys

from provider import get_provider, run_jobs
from styles import compose_collage_prompt, STYLE_LIBRARY, THEME_PRESETS, resolve_theme

IMAGE_MODEL = "google/nano-banana-2/text-to-image"
# candidates are THEME names (full look bundles); Claude picks topic-fitting ones
DEFAULT_CANDIDATES = ["american-retro", "swiss-modern", "punk-zine", "atomic-age"]


def first_shot(beat):
    return beat["shots"][0] if beat.get("shots") else beat


def run(project_dir, styles=None, beat_index=0):
    styles = styles or DEFAULT_CANDIDATES
    with open(os.path.join(project_dir, "beats.json")) as f:
        doc = json.load(f)
    aspect = doc.get("aspect", "16:9")
    beat = doc["beats"][beat_index]
    shot = first_shot(beat)
    scene, bg = shot["scene"], beat.get("bg", "warm ochre")
    tcn, ten = beat.get("title_cn", ""), beat.get("title_en", "")
    out = os.path.join(project_dir, "style-bakeoff"); os.makedirs(out, exist_ok=True)

    prov = get_provider(doc.get("provider"))
    specs = {}
    for name in styles:
        tp = resolve_theme(name) or {}              # theme name -> full look bundle
        prompt = compose_collage_prompt(scene, tcn, ten, bg, aspect,
                                        style=tp.get("idiom", name), palette=tp.get("palette"),
                                        type_style=tp.get("type_style"), finish=tp.get("finish"))
        specs[name] = (lambda p=prompt: prov.submit_image(IMAGE_MODEL, p,
                                                          aspect_ratio=aspect, resolution="2k"))
        tag = "library" if name in STYLE_LIBRARY else "custom"
        print(f"[{name}] ({tag}) queued")

    done = run_jobs(prov, specs, poll_s=3, stall_s=75, max_retries=2, deadline_s=240)

    for name, url in done.items():
        if url:
            prov.download(url, os.path.join(out, f"{name}.jpg"))
    print(f"\nsaved candidates to {out} — review, then set \"collage_style\" in beats.json.")


if __name__ == "__main__":
    proj = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else
                           os.path.join(os.path.dirname(__file__), "..", "out", "money-60s"))
    styles = sys.argv[2].split(",") if len(sys.argv) > 2 else None
    bi = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    run(proj, styles, bi)
