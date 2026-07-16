#!/usr/bin/env python3
"""
A-roll clip stage: cut each ASR beat's time range out of the source recording
(see asr_beats.py) and re-style it as a mixed-media collage clip, keeping the
presenter's own performance -- lip movement, eye-line, gestures -- frame-for-
frame. Unlike B-roll there is no synthesized poster to animate: the "keyframe"
IS the presenter's real footage, so this talks to video-edit / reference-to-
video models instead of image-to-video.

Model routing (validated 2026-07-16 against a real production clip):
  1. google/gemini-omni-flash/video-edit (default). Accepts real people and a
     PHOTOGRAPHIC paper-cutout sticker treatment on the presenter (proven).
     Rejects (1010002) a prompt that asks it to redraw/halftone-texture the
     face itself -- tried both a strong and a softened phrasing, both
     rejected, so build_prompt() below never asks for that.
  2. bytedance/seedance-2.0/reference-to-video (fallback) for any beat Omni
     rejects.
Kling O3 pro's video-edit/reference-to-video were also validated as a further
fallback (they don't policy-block this content) but default to a flat vector-
illustration look rather than photographic, so they're not the auto-fallback
here -- wire them in via video_model_fallback if you've confirmed the look.

Usage: python3 aroll_clips.py <project_dir>
"""
import json
import os
import subprocess
import sys

from provider import get_provider, run_jobs
from styles import resolve_theme, resolve_video_aspect

PRIMARY_MODEL = "google/gemini-omni-flash/video-edit"
FALLBACK_MODEL = "bytedance/seedance-2.0/reference-to-video"


def cut_segment(src, start, end, dest, pad=0.15):
    """Cut this beat's [start,end] (+ a small pad) out of the source, re-encoded
    so it's a clean, independently seekable upload for the video-edit call."""
    dur = max(end - start, 0.1) + pad
    ss = max(start - pad / 2, 0)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{ss:.2f}", "-i", src,
                    "-t", f"{dur:.2f}", "-c:v", "libx264", "-c:a", "aac",
                    "-pix_fmt", "yuv420p", dest], check=True)


def build_prompt(theme, content_beats=""):
    """Presenter-lock + theme block. Only the B1 pattern Omni actually accepts:
    a PHOTOGRAPHIC paper-cutout sticker (silhouette/edge re-styled), never a
    redrawn or halftone-textured face -- that's the one thing that got this
    content rejected, in both a strong and a softened phrasing."""
    tp = theme or {}
    idiom = tp.get("idiom", "american-retro")
    palette = tp.get("palette", "bold retro primaries")
    type_style = tp.get("type_style", "bold condensed headlines")
    finish = tp.get("finish", "aged paper, high contrast")
    beats_line = f"\n\nCONTENT BEATS: {content_beats}" if content_beats else ""
    return (
        "Transform my raw talking-head video into a mixed-media collage motion graphic.\n\n"
        "TALKING-HEAD LOCK (most important):\n"
        "The presenter is a PHOTOGRAPHIC paper cut-out sticker with a bold black printed "
        "outline and a torn-paper silhouette edge -- her actual photographic likeness, "
        "facial performance, LIP MOVEMENTS, eye-line and hand gestures follow the source "
        "video frame-for-frame, unmodified. Do NOT re-texture, redraw, or halftone-print the "
        "face or skin itself -- only the silhouette edge and the world around her are paper-"
        "collage. Keep ALL motion, timing and framing from the source. Keep the presenter "
        "centered, matching the source video's own orientation.\n\n"
        f"STYLE (background & props): {idiom}. Palette: {palette}. Typography: {type_style}. "
        f"Finish: {finish}. Clearly layered hand-cut paper cut-outs with visible torn and "
        "scissor-cut edges, tape corners and soft real paper drop shadows, on a bold flat "
        "paper background. Halftone print dots, newspaper-clipping scraps, paper-stencil "
        "shapes, aged paper texture. PRINTED / illustrated cut-outs for the background and "
        f"props, NOT CGI, NOT 3D.{beats_line}\n\n"
        "CONSTRAINTS: background elements and stamps never cover her face or hands; "
        "everything except the presenter's face/skin reads as printed paper."
    )


def video_params(model, video_url, aspect, dur):
    """Per-model request body. Audio is intentionally NOT requested/trusted from
    any of these models -- aroll_assemble.py always remuxes the original beat
    segment's own audio afterward, so lip-sync never depends on a model's
    audio-passthrough behavior (Omni's video-edit schema doesn't even expose
    one)."""
    if "seedance" in model:
        return dict(reference_videos=[video_url], duration=max(4, min(15, round(dur))),
                    ratio=aspect, resolution="1080p", generate_audio=False)
    if "kling-video-o3-pro/reference-to-video" in model:
        return dict(video=video_url, aspect_ratio=aspect, duration=max(3, min(15, round(dur))),
                    keep_original_sound=False, sound=False)
    if "kling" in model:                      # video-edit: follows input, no aspect param
        return dict(video=video_url, keep_original_sound=False)
    return dict(video=video_url)              # gemini-omni-flash/video-edit


def run(project_dir, only=None):
    bpath = os.path.join(project_dir, "beats.json")
    with open(bpath) as f:
        doc = json.load(f)
    if doc.get("mode") != "aroll":
        raise SystemExit("beats.json has no \"mode\": \"aroll\" -- run asr_beats.py first, "
                         "or use clips.py for a B-roll project.")
    src = doc["source_video"]
    aspect = doc.get("aspect", "9:16")
    theme = resolve_theme(doc.get("theme")) or {}
    primary = doc.get("video_model", PRIMARY_MODEL)
    fallback = doc.get("video_model_fallback", FALLBACK_MODEL)
    seg_dir = os.path.join(project_dir, "segments")
    clip_dir = os.path.join(project_dir, "clips")
    os.makedirs(seg_dir, exist_ok=True)
    os.makedirs(clip_dir, exist_ok=True)

    prov = get_provider(doc.get("provider"))

    def gate_aspect(model):
        resolved, exact = resolve_video_aspect(aspect, model)
        if not exact and not doc.get("aspect_approx_confirmed"):
            print(f"ASPECT MISMATCH on {model}: project aspect \"{aspect}\" has no exact "
                  f"match; nearest supported is \"{resolved}\". Confirm with the user, then "
                  f"set \"aspect_approx_confirmed\": true in beats.json to proceed.")
            return None
        return resolved or aspect

    a_primary = gate_aspect(primary)
    if a_primary is None:
        return

    # ---- cut + upload each beat's segment, queue the primary-model submission ----
    specs, meta = {}, {}
    for beat in doc["beats"]:
        key = str(beat["id"])
        if only and key not in only:
            continue
        seg_path = os.path.join(seg_dir, f"seg_{key}.mp4")
        cut_segment(src, beat["start"], beat["end"], seg_path)
        url = prov.upload(seg_path)
        prompt = build_prompt(theme, beat.get("content_beats", ""))
        params = video_params(primary, url, a_primary, beat["dur"])
        specs[key] = (lambda m=primary, p=prompt, pr=params: prov.submit_video(m, p, **pr))
        meta[key] = {"beat": beat, "seg_path": seg_path, "url": url}
        print(f"[{key}] queued on {primary.split('/')[-2]} ({beat['dur']}s)")

    done = run_jobs(prov, specs, poll_s=8, stall_s=240, max_retries=1, deadline_s=900)

    # ---- fallback pass: only the beats the primary model rejected/failed ----
    retry_keys = [k for k, u in done.items() if not u]
    if retry_keys:
        a_fallback = gate_aspect(fallback)
        if a_fallback is None:
            print(f"skipping fallback for beats {retry_keys}: aspect gate blocked above")
        else:
            print(f"[{fallback.split('/')[-2]}] retrying beats {retry_keys}")
            fb_specs = {}
            for key in retry_keys:
                m = meta[key]
                prompt = build_prompt(theme, m["beat"].get("content_beats", ""))
                params = video_params(fallback, m["url"], a_fallback, m["beat"]["dur"])
                fb_specs[key] = (lambda mo=fallback, p=prompt, pr=params:
                                 prov.submit_video(mo, p, **pr))
            fb_done = run_jobs(prov, fb_specs, poll_s=8, stall_s=240, max_retries=1, deadline_s=900)
            done.update({k: v for k, v in fb_done.items() if v})

    for key, url in done.items():
        beat = meta[key]["beat"]
        if not url:
            print(f"[{key}] FAILED on both primary and fallback -- beat will be missing "
                  f"from the assembled film")
            continue
        dest = os.path.join(clip_dir, f"clip_{key}.mp4")
        prov.download(url, dest)
        beat["clip_path"] = dest
        print(f"[{key}] saved {dest}")

    with open(bpath, "w") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print("updated", bpath)


if __name__ == "__main__":
    proj = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "out", "aroll-demo")
    only = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else None
    run(os.path.abspath(proj), only=only)
