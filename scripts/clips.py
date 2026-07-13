#!/usr/bin/env python3
"""
Clip stage: animate each SHOT's keyframe into a short clip (Gemini Omni Flash
image-to-video), using the shot's own duration and a punchy collage
motion-graphic prompt (5-axis + the shot's specific move). More, shorter shots
= more cuts = less "one static frame for 10s".

Usage: python3 clips.py <project_dir>   (default: out/tang-30s)
"""
import json
import os
import sys

from provider import get_provider, run_jobs
from styles import resolve_theme

VIDEO_MODEL = "google/gemini-omni-flash/image-to-video"


def shots_of(beat):
    if beat.get("shots"):
        for s in beat["shots"]:
            yield s, f"{beat['id']}{s.get('id','')}"
    else:
        yield beat, f"{beat['id']}"


# Camera-move vocab. The first group is flat-collage-SAFE (default). The "bold" group can warp
# the flat art / smear text (verified) — they're AVAILABLE, not banned: use with constraints
# "loose" and expect to re-roll. Any string not in the dict passes through verbatim too.
CAMERA_VOCAB = {
    "static":   "a locked-off static camera (no camera move)",
    "push_in":  "one very slow smooth push-in (uniform scale-up, Ken-Burns)",
    "pull_out": "one slow smooth pull-out (uniform scale-down) revealing the full scene",
    "pan":      "one slow horizontal pan across the frame (flat translate, no perspective shift)",
    "tilt":     "one slow vertical tilt (flat translate, no perspective shift)",
    "parallax": "a gentle multi-layer parallax drift (paper layers moving at slightly different "
                "speeds), the camera otherwise steady",
    # bold / experimental (pair with constraints="loose", re-roll):
    "orbit":     "a slow 3D orbit / camera arc around the scene",
    "dolly_zoom": "a dolly-zoom (vertigo) — push in while the background pulls back",
    "roll":      "a slow camera roll / canted rotation",
    "whip":      "a fast whip-pan sweep that settles",
}

AMPLITUDE = {
    "calm":   "subtle, restrained amplitude",
    "punchy": "lively, energetic amplitude with clear, bold movement",
    "max":    "high-energy amplitude — elements burst, scatter and fly boldly",
}

# Neutral fallback when a shot doesn't specify element_motion. Prefer per-shot AI-authored
# element_motion that fits the scene — do NOT force a flying element into every shot.
DEFAULT_ELEMENT = ("several cut-out elements move naturally with the scene — they bob, tilt, "
                   "slide, drift and scatter; halftone dots pulse")


def collage_prompt(camera, element_motion=None, feel=None, palette=None, amplitude="punchy",
                   has_title=True, constraints="strict"):
    """Collage motion prompt. `constraints`: 'strict' = defect guards on (flat-2D, one-way,
    no-morph) for text-heavy explainers; 'loose' = let the model explore (3D/bold moves), keep
    only the essentials. Text is hard-protected ONLY when the shot has a headline (has_title)."""
    cam = CAMERA_VOCAB.get(camera, camera)
    element = element_motion or DEFAULT_ELEMENT
    feel = feel or "tactile, editorial, a page from a scrapbook"
    palette = palette or "the still's existing palette, high contrast"
    amp = AMPLITUDE.get(amplitude, AMPLITUDE["punchy"])
    text_lock = ("Keep the HEADLINE TEXT sharp, legible and stable — do not warp or wobble the "
                 "lettering. " if has_title else "")
    if constraints == "loose":
        guard = (text_lock + "Keep the paper-collage look (printed cut-outs, not photoreal); "
                 "avoid a subject melting into shapeless goo. Otherwise explore freely.")
    else:  # strict — defect guards for clean, text-heavy explainers
        guard = (text_lock + "Keep the layout stable. Stay flat 2D — no 3D rotation, no "
                 "perspective change, camera parallel to the poster. ONE continuous move that "
                 "does not loop, retract or reset. Rigid paper — no morph/melt. Animate the "
                 "motion only; don't re-render the picture.")
    return (
        "Animate this still into a mixed-media paper-collage MOTION GRAPHIC, printed cut-outs, "
        "not photoreal.\n"
        f"CAMERA (one move only): {cam}.\n"
        f"ELEMENT MOTION (rich — this is the energy, {amp}): {element}. Elements move as paper "
        "cut-outs (slide, flap, hinge, pop, scatter, fly).\n"
        "AESTHETIC: keep the torn-paper, tape, halftone, newsprint and paper-stencil textures "
        "and the bold flat background.\n"
        f"FEEL: {feel}.\nCOLOR: {palette}.\n"
        f"CONSTRAINTS: {guard}"
    )


def painterly_prompt(motion):
    return (f"Animate this classical Chinese painting with subtle, tasteful motion: {motion}. "
            f"Keep the painted style, textures and all on-screen text intact and stable. "
            f"Gentle, cinematic, no morphing, no new objects.")


def run(project_dir, only=None):
    bpath = os.path.join(project_dir, "beats.json")
    with open(bpath) as f:
        doc = json.load(f)
    aspect = doc.get("aspect", "16:9")
    style = doc.get("style", "painterly")
    _theme = resolve_theme(doc.get("theme")) or {}
    motion_style = doc.get("motion_style") or _theme.get("motion_style", "punchy")  # calm|punchy|max
    constraints = doc.get("constraints", "strict")   # strict = defect guards on | loose = explore
    model = doc.get("video_model", VIDEO_MODEL)   # Seedance for real people; Omni otherwise
    vid_res = doc.get("video_resolution", "720p")  # 720p default; Seedance also 480p/1080p (Omni is 720p-only)
    clip_dir = os.path.join(project_dir, "clips")
    os.makedirs(clip_dir, exist_ok=True)

    prov = get_provider(doc.get("provider"))
    specs, by_key = {}, {}
    for beat in doc["beats"]:
        for shot, key in shots_of(beat):
            if only and key not in only:
                continue
            url = shot.get("keyframe_url")
            if not url and shot.get("keyframe_path") and os.path.exists(shot["keyframe_path"]):
                # user-provided keyframe (e.g. hand-made collage card) -> upload it
                url = prov.upload(shot["keyframe_path"])
                shot["keyframe_url"] = url
                print(f"[{key}] uploaded provided keyframe -> {url}")
            if not url:
                print(f"[{key}] no keyframe — provide keyframe_path or run keyframes.py")
                continue
            # new schema: camera_move (token) + element_motion (rich). Back-compat: old `motion`.
            camera = shot.get("camera_move") or shot.get("motion", "push_in")
            element = shot.get("element_motion")
            if style == "collage":
                prompt = collage_prompt(camera, element_motion=element, feel=beat.get("feel"),
                                        palette=beat.get("bg"), amplitude=motion_style,
                                        has_title=shot.get("title", True), constraints=constraints)
            else:
                prompt = painterly_prompt(shot.get("motion", camera))
            dur = int(shot.get("dur", 10))
            if "seedance" in model:                 # ratio (not aspect_ratio); real-person OK
                params = dict(image=url, duration=dur, ratio=aspect,
                              resolution=vid_res, generate_audio=False)
            elif "kling" in model:                   # no aspect param (follows input); allows real people
                params = dict(image=url, duration=dur, sound=False)
            else:                                    # gemini omni flash
                params = dict(image=url, duration=dur, aspect_ratio=aspect, resolution="720p")
            specs[key] = (lambda m=model, p=prompt, pr=params: prov.submit_video(m, p, **pr))
            by_key[key] = shot
            print(f"[{key}] queued ({dur}s, {model.split('/')[1]})")

    done = run_jobs(prov, specs, poll_s=5, stall_s=240, max_retries=2, deadline_s=1200)

    for key, url in done.items():
        if not url:
            continue
        dest = os.path.join(clip_dir, f"clip_{key}.mp4")
        prov.download(url, dest)
        shot = by_key[key]
        shot["clip_url"] = url
        shot["clip_path"] = dest
        print(f"[{key}] saved {dest}")

    with open(bpath, "w") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print("updated", bpath)


if __name__ == "__main__":
    proj = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "out", "tang-30s")
    only = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else None
    run(os.path.abspath(proj), only=only)
