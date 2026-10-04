#!/usr/bin/env python3
"""
Host stage 1: the two STILLS for every host shot.

  person plate  the presenter image carried over verbatim as a cut-out print on flat chroma
                green (nano-banana-2/edit)
  world plate   the collage world with the presenter's area left empty and no people in it
                (nano-banana-2/text-to-image, same theme as the rest of the film)

Look at both before running host_clips.py — the plates are the cheap checkpoint (~$0.24 per
shot). Check that the green is flat and even, the face is the presenter's and not a redraw,
and the world has nothing in the empty region.

Usage: python3 host_plates.py <project_dir> [only_ids] [--redo]
       only_ids is a comma list of shot keys, e.g. 1a,7a
"""
import json
import os
import sys

from host import (CHROMA_HEX, PERSON_PLATE_MODEL, PERSON_PLATE_PROMPT, WORLD_PLATE_MODEL,
                  WORLD_PLATE_SUFFIX, host_cfg, layout_for, validate)
from provider import get_provider, run_jobs
from styles import compose_collage_prompt, image_params, resolve_theme


def run(project_dir, only=None, redo=False):
    bpath = os.path.join(project_dir, "beats.json")
    with open(bpath) as f:
        doc = json.load(f)
    shots = validate(doc)
    aspect = doc.get("aspect", "16:9")
    layout = layout_for(aspect)
    cfg = host_cfg(doc)
    img_res = doc.get("image_resolution", "2k")
    theme = resolve_theme(doc.get("theme")) or {}
    collage_style = theme.get("idiom") or doc.get("collage_style", "american-retro")
    kf_dir = os.path.join(project_dir, "keyframes")
    os.makedirs(kf_dir, exist_ok=True)

    prov = get_provider(doc.get("provider"))
    if cfg.get("_avatar_src") == cfg["avatars"] and cfg.get("_avatar_urls"):
        avatar_urls = cfg["_avatar_urls"]                 # cached upload, same source images
    else:
        avatar_urls = [a if a.startswith("http") else prov.upload(os.path.expanduser(a))
                       for a in cfg["avatars"]]
    doc["host"]["_avatar_src"], doc["host"]["_avatar_urls"] = cfg["avatars"], avatar_urls

    person_prompt = PERSON_PLATE_PROMPT.format(
        subject=cfg["subject"], outfit_lock=cfg["outfit_lock"], placement=layout["placement"],
        chroma=CHROMA_HEX, aspect=aspect)

    specs, meta = {}, {}
    for beat, shot, key in shots:
        if only and key not in only:
            continue
        if redo or not shot.get("person_plate_url"):
            specs[f"{key}-person"] = (lambda: prov.submit_image(
                PERSON_PLATE_MODEL, person_prompt, images=avatar_urls,
                **image_params(PERSON_PLATE_MODEL, aspect, img_res)))
            meta[f"{key}-person"] = (shot, "person_plate", person_prompt)
        if redo or not shot.get("world_plate_url"):
            world_prompt = compose_collage_prompt(
                shot["scene"], "", "", beat.get("bg", "flat cream paper"), aspect,
                with_title=False, style=collage_style,
                palette=theme.get("palette") or doc.get("palette"),
                type_style=theme.get("type_style") or doc.get("type_style"),
                finish=theme.get("finish") or doc.get("finish"),
            ) + WORLD_PLATE_SUFFIX.format(world_clear=layout["world_clear"])
            specs[f"{key}-world"] = (lambda p=world_prompt: prov.submit_image(
                WORLD_PLATE_MODEL, p, **image_params(WORLD_PLATE_MODEL, aspect, img_res)))
            meta[f"{key}-world"] = (shot, "world_plate", world_prompt)

    if not specs:
        print("all plates already exist (use --redo to regenerate)")
    done = run_jobs(prov, specs, poll_s=3, stall_s=90, max_retries=2, deadline_s=420)

    for k, url in done.items():
        if not url:
            print(f"[{k}] FAILED")
            continue
        shot, field, prompt = meta[k]
        key = k.rsplit("-", 1)[0]
        dest = os.path.join(kf_dir, f"{field}_{key}.jpg")
        prov.download(url, dest)
        shot[f"{field}_url"] = url
        shot[f"{field}_path"] = dest
        shot[f"{field}_prompt"] = prompt
        # a new plate makes its video (and the composite) stale
        side = field.split("_")[0]                 # person | world
        for stale in (f"{side}_clip_path", f"{side}_clip_url", "clip_path", "clip_url"):
            shot.pop(stale, None)
        print(f"[{k}] saved {dest}")

    with open(bpath, "w") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print("updated", bpath)
    print("NEXT: open the plates in keyframes/ and check them before host_clips.py")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit("usage: python3 host_plates.py <project_dir> [only_ids] [--redo]")
    only = set(args[1].split(",")) if len(args) > 1 else None
    run(os.path.abspath(args[0]), only, redo="--redo" in sys.argv)
