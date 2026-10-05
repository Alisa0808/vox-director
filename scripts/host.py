#!/usr/bin/env python3
"""
Host mode shared module: layout table, prompt templates, validation, cost estimate.

A host shot (`"kind": "host"`) is a presenter speaking the beat's narration on camera,
lip-synced, standing inside the collage world. It is built from TWO plates generated
separately and keyed together (see references/host-mode.md):

  person plate  green-screen still of the presenter  -> Seedance 2.0 reference-to-video
  world plate   the collage with that area left empty -> Gemini Omni image-to-video

host_plates.py makes the stills, host_clips.py animates + composites them. Everything that
depends on the frame spec lives in HOST_LAYOUTS below, so a new aspect ratio is one new
entry here (plus a validation run) rather than an edit to the pipeline.
"""
import math
import os
import re
import subprocess

# ---- models -----------------------------------------------------------------------------
PERSON_PLATE_MODEL = "google/nano-banana-2/edit"
WORLD_PLATE_MODEL = "google/nano-banana-2/text-to-image"
PERSON_VIDEO_MODEL = "bytedance/seedance-2.0/reference-to-video"   # default; host.person_video_model overrides
WORLD_VIDEO_MODEL = "google/gemini-omni-flash/image-to-video"   # default; host.world_video_model overrides

CHROMA = "0x00B140"          # key colour as ffmpeg wants it
CHROMA_HEX = "#00B140"       # the same colour as the prompt says it
TAIL = 0.5                   # assemble.py's breathing room after the narration
MIN_VIDEO_S = 4              # shortest Seedance clip we request
MAX_VIDEO_S = 10             # Omni image-to-video is verified up to 10s (Seedance allows 15)

# ---- layout registry: ONE entry per supported aspect ratio ------------------------------
# regions          position name -> (region phrase, REGION shouted in the plate prompt)
# default_position / default_head   the validated defaults (head = fraction of frame height)
# placement        template for the person-plate prompt
# world_clear      what the world plate must keep empty so the presenter fits there
# mouth_box        (x, y, w, h) fractions of the frame for lipsync_score.py. Valid ONLY for the
#                  default position + size; with a custom one pass --mouth to lipsync_score.py
# Users adjust the presenter with host.position and host.size in beats.json (resolve_layout).
HOST_LAYOUTS = {
    "16:9": {
        "regions": {"left": ("left third", "LEFT THIRD"),
                    "center": ("middle third", "MIDDLE THIRD"),
                    "right": ("right third", "RIGHT THIRD")},
        "default_position": "left",
        "default_head": 0.25,
        "placement": ("They are shown from the waist up, standing and facing the camera like a "
                      "documentary host, positioned in the {REGION} of the frame with their head "
                      "about {head} of the frame height — never a big head-and-shoulders crop."),
        "world_clear": ("Leave the {region} of the composition clearly empty — no element, scrap "
                        "or text intrudes there."),
        "mouth_box": (0.215, 0.408, 0.07, 0.065),
    },
    "9:16": {
        "regions": {"lower": ("lower half", "LOWER HALF")},
        "default_position": "lower",
        "default_head": 1 / 7,
        "placement": ("They are shown from the waist up, standing and facing the camera like a "
                      "documentary host, centred horizontally in the {REGION} of the frame with "
                      "the body running off the bottom edge and their head about {head} of the "
                      "frame height, the top of the head near the middle of the frame — never a "
                      "big head-and-shoulders crop."),
        "world_clear": ("Leave the {region} of the composition clearly empty — no element, scrap "
                        "or text intrudes there."),
        "mouth_box": (0.45, 0.437, 0.12, 0.035),   # measured on the 9:16 test plate (2026-10-06)
    },
}
_HEAD_WORDS = {0.25: "one quarter", 0.2: "one fifth", 1 / 7: "one seventh", 1 / 6: "one sixth",
               0.5: "one half", 1 / 3: "one third"}


def head_phrase(h):
    for k, w in _HEAD_WORDS.items():
        if abs(h - k) < 1e-6:
            return w
    return f"{round(h * 100)} percent"


# ---- prompts (validated wording from the Silicon Valley film; pronouns made neutral) -----
PERSON_PLATE_PROMPT = (
    "The attached reference image(s) are the finished character design of the host — the FIRST "
    "image is authoritative. The {subject} is already exactly right: DO NOT redesign, restyle, "
    "repaint or re-illustrate them. Carry them over verbatim — the same face, the same features "
    "and proportions, the same skin rendering, the same hair, the same soft neutral "
    "expression{outfit_lock}. They are a GLOSSY FULL-COLOUR PRINT of that image, scissor-cut "
    "around their silhouette with a thin torn WHITE paper border. {placement} THE ENTIRE REST OF "
    "THE FRAME IS ONE COMPLETELY FLAT, EVEN, PURE CHROMA-KEY GREEN ({chroma}) — a solid unbroken "
    "green field with no gradient, no texture, no shading, no paper, no scenery, no scraps, no "
    "shadow and no text of any kind. Nothing at all except their cut-out print on flat green. "
    "Aspect ratio {aspect}."
)

WORLD_PLATE_SUFFIX = (
    " No people and no figures anywhere in the image. {world_clear} Newspaper scraps carry "
    "completely UNREADABLE blurred micro-text."
)

# One reference image, bound explicitly with @image1. A second image made the model reconcile
# two different pictures instead of animating the plate (correlation 0.033 vs 0.095).
PERSON_VIDEO_PROMPT = (
    "The {subject} in @image1 speaks to camera as a documentary host, their lips synced "
    "precisely to audio 1. Their face, features, face shape, skin and hair stay exactly as in "
    "@image1 — do not restyle, age, slim or beautify them. Keep the mouth movement SMALL and "
    "natural: gentle close-lipped articulation with only slight jaw movement, never a wide open "
    "mouth, never bared teeth or a gaping shape. They have a warm, lively facial expression — "
    "small friendly head movements, natural blinks, eyebrows and eyes alive as they talk — and "
    "gesture easily with one hand. They keep their exact position and scale in the {region} "
    "of the frame{outfit_clause}, still a scissor-cut print with its torn white paper border. "
    "THE GREEN BACKGROUND MUST STAY A COMPLETELY FLAT, EVEN, UNIFORM PURE GREEN for the whole "
    "shot — no gradient, no shading, no shadows cast onto it, no texture, no objects, nothing "
    "else appears on it. The camera is locked off: no push-in, no pan, no zoom, no reframing. "
    "{feel}"
)

# The camera must be locked on BOTH plates: if one moved, the composite would slide apart.
WORLD_VIDEO_PROMPT = (
    "Animate this still into a living paper-collage motion graphic, flat 2D printed cut-outs, "
    "not photoreal. The camera is completely locked off — no push-in, no pan, no zoom, no "
    "reframing whatsoever.\n"
    "ELEMENT MOTION (this is the whole point — the world is alive the entire time): every "
    "element already in the still moves, but each one KEEPS ITS OWN EXACT SHAPE while it does. "
    "{element_motion}\n"
    "Keep the {region} of the frame clear and calm — nothing drifts into it.\n"
    "AESTHETIC: preserve the printed, halftone, torn paper and tape textures of the still "
    "exactly, and keep the flat background colour.\n"
    "CONSTRAINTS: rigid flat paper layers only — no 3D rotation, no perspective change, no "
    "morphing or melting. Nothing new enters the frame, no element is added or removed, and "
    "every element is still present at the end. Animate the motion only; do not re-render or "
    "redraw the picture. {feel}"
)

# Used when a shot has no element_motion. Safe, but the recipe works best when the author names
# each element and pins its shape (Omni turned a propeller plane into a paper dart, and gave a
# flat sun rays, whenever the prompt only said "add nothing new").
DEFAULT_WORLD_MOTION = (
    "The torn-paper layers drift slowly at slightly different depths in continuous gentle "
    "parallax. Any figure, vehicle or object stays exactly the same cut-out it is in the still "
    "and only drifts, bobs or sways in place — it never changes into another shape. The "
    "geometric paper scraps bob and rotate only a few degrees. The tape corners and torn paper "
    "edges flutter. Motion amplitude is subtle and restrained throughout."
)

# ---- cost (2026-07-30 official pages — verify before relying on it) ----------------------
PRICE_IMAGE_2K = 0.12            # per still (nano-banana-2, 2k)
PRICE_PERSON_PER_S = 0.194       # Seedance 2.0 720p, after the -20% promo (list 0.2429)
PRICE_PERSON_FAST_PER_S = 0.058  # Seedance 2.0 Fast: ESTIMATE = standard x 0.3 (the catalog ratio)
PRICE_WORLD_PER_S = 0.13         # Omni, billed from 3s


def article_free(phrase):
    """'a cream hoodie' -> 'cream hoodie' (prompts supply their own article)."""
    return re.sub(r"^(a|an|the)\s+", "", (phrase or "").strip(), flags=re.I)


def person_model(doc):
    """The person-video model: host.person_video_model, else the Seedance 2.0 default."""
    return (doc.get("host") or {}).get("person_video_model") or PERSON_VIDEO_MODEL


def world_model(doc):
    return (doc.get("host") or {}).get("world_video_model") or WORLD_VIDEO_MODEL


def person_price(model):
    return PRICE_PERSON_FAST_PER_S if "fast" in model else PRICE_PERSON_PER_S


def host_cfg(doc):
    """The project-level `host` block with prompt-ready fields filled in."""
    h = dict(doc.get("host") or {})
    avatar = h.get("avatar")
    h["avatars"] = [avatar] if isinstance(avatar, str) else list(avatar or [])
    h["subject"] = h.get("subject") or "presenter"
    outfit = article_free(h.get("outfit"))
    h["outfit_lock"] = f", and the same {outfit}" if outfit else ""
    h["outfit_clause"] = f" and their {outfit} is unchanged" if outfit else ""
    return h


def layout_for(aspect):
    if aspect not in HOST_LAYOUTS:
        raise SystemExit(f"host mode has no layout for aspect \"{aspect}\" (supported: "
                         f"{', '.join(HOST_LAYOUTS)}). Add an entry to HOST_LAYOUTS in "
                         f"scripts/host.py and validate it before using another ratio.")
    return HOST_LAYOUTS[aspect]


def resolve_layout(doc):
    """The layout for this project: the aspect's defaults, adjusted by the user's
    host.position (a region name from the layout) and host.size (head height as a fraction of
    the frame height, 0.08-0.6). The model treats size as a hint, not a measurement, so check
    the person plate before paying for video. Returns region/placement/world_clear and
    mouth_box (None when position or size is customised)."""
    base = layout_for(doc.get("aspect", "16:9"))
    h = doc.get("host") or {}
    pos = h.get("position") or base["default_position"]
    if pos not in base["regions"]:
        raise SystemExit(f"host.position \"{pos}\" is not available for {doc.get('aspect', '16:9')} "
                         f"(choose one of: {', '.join(base['regions'])})")
    try:
        head = float(h.get("size") or base["default_head"])
    except (TypeError, ValueError):
        raise SystemExit("host.size must be a number: head height as a fraction of frame height")
    if not 0.08 <= head <= 0.6:
        raise SystemExit(f"host.size {head} is outside 0.08-0.6 (head height / frame height)")
    region, shout = base["regions"][pos]
    custom = pos != base["default_position"] or abs(head - base["default_head"]) > 1e-9
    return {"region": region,
            "placement": base["placement"].format(REGION=shout, head=head_phrase(head)),
            "world_clear": base["world_clear"].format(region=region),
            "mouth_box": None if custom else base["mouth_box"]}


def probe_dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True).stdout
    try:
        return float(out.strip())
    except ValueError:
        return 0.0


def host_shots(doc):
    """Yield (beat, shot, key) for every shot with kind == 'host'."""
    for beat in doc["beats"]:
        for shot in beat.get("shots") or []:
            if shot.get("kind") == "host":
                yield beat, shot, f"{beat['id']}{shot.get('id', '')}"


def reference_audio(beat):
    """The beat's ORIGINAL narration, not the model-sung track host_clips swaps in.

    host_clips.py replaces `narration_audio` with the presenter clip's own audio and keeps the
    original as `narration_audio_reference`. If audio.py has since regenerated the narration,
    `narration_audio` no longer equals the adopted track and is itself the new original.
    """
    cur = beat.get("narration_audio")
    if beat.get("host_own_audio") and cur == beat["host_own_audio"]:
        return beat.get("narration_audio_reference") or cur
    return cur


def video_seconds(narration_s):
    """Clip length: cover the narration plus assemble's tail so the beat is never stretched."""
    return min(MAX_VIDEO_S, max(MIN_VIDEO_S, math.ceil(narration_s + TAIL)))


def validate(doc, need_audio=False):
    """Check host-mode preconditions and return [(beat, shot, key)]. Exits with ALL problems."""
    shots = list(host_shots(doc))
    if not shots:
        raise SystemExit("no shot has \"kind\": \"host\" — nothing to do")
    problems = []
    resolve_layout(doc)
    cfg = host_cfg(doc)
    if not cfg["avatars"]:
        problems.append("beats.json needs host.avatar (a path/URL to the presenter image)")
    for a in cfg["avatars"]:
        if not a.startswith("http") and not os.path.exists(os.path.expanduser(a)):
            problems.append(f"host.avatar not found: {a}")
    for beat in doc["beats"]:
        hs = [s for s in (beat.get("shots") or []) if s.get("kind") == "host"]
        if hs and len(beat["shots"]) != 1:
            problems.append(f"beat {beat['id']}: a host beat must have exactly ONE shot (the "
                            f"presenter speaks the whole beat)")
    for beat, shot, key in shots:
        if not shot.get("scene"):
            problems.append(f"[{key}] needs a \"scene\" (the WORLD plate, no people)")
        if need_audio:
            ref = reference_audio(beat)
            if not ref or not os.path.exists(ref):
                problems.append(f"[{key}] no narration audio — run audio.py first")
                continue
            dur = probe_dur(ref)
            if dur + TAIL > MAX_VIDEO_S:
                problems.append(f"[{key}] narration is {dur:.1f}s; a host beat must be "
                                f"<= {MAX_VIDEO_S - TAIL:.1f}s (Omni's verified clip cap is "
                                f"{MAX_VIDEO_S}s) — split the line into two beats")
            elif dur < 3:
                print(f"[{key}] warning: narration is only {dur:.1f}s; the clip is "
                      f"{MIN_VIDEO_S}s minimum, so the presenter will stand silent for the rest")
    if problems:
        raise SystemExit("host mode:\n  - " + "\n  - ".join(problems))
    return shots


def estimate(person_s, world_s, person_per_s=PRICE_PERSON_PER_S):
    """Rough cost lines + total for the videos still to generate.

    person_s / world_s: shot key -> seconds to generate (absent = already exists, free).
    """
    lines, total = [], 0.0
    for key in sorted(set(person_s) | set(world_s)):
        p = person_s.get(key, 0) * person_per_s
        w = world_s.get(key, 0) * PRICE_WORLD_PER_S
        lines.append(f"  [{key}] person {person_s.get(key, 0)}s ${p:.2f} + "
                     f"world {world_s.get(key, 0)}s ${w:.2f}")
        total += p + w
    return lines, total
