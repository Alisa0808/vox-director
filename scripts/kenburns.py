#!/usr/bin/env python3
"""
Ken-Burns fallback clip stage (NO AI video model): turn each beat's keyframe
into a slow moving clip with ffmpeg zoompan. Use when AI i2v models refuse the
content (e.g. real-celebrity / brand collage cards get blocked by both Omni and
Seedance for likeness / digital-rights reasons).

Each card: a blurred cover fills the frame behind the sharp, fully-visible card,
then a slow push-in/out (direction alternates per beat) gives it life.

Usage: python3 kenburns.py <project_dir> [shotkeys]
"""
import json
import os
import subprocess
import sys

FPS = 25
RES = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080), "3:4": (1080, 1440)}


def shots_of(beat):
    if beat.get("shots"):
        for s in beat["shots"]:
            yield s, f"{beat['id']}{s.get('id','')}"
    else:
        yield beat, f"{beat['id']}"


def run(project_dir, only=None):
    bpath = os.path.join(project_dir, "beats.json")
    with open(bpath, encoding="utf-8") as f:
        doc = json.load(f)
    W, H = RES.get(doc.get("aspect", "9:16"), (1080, 1920))
    clip_dir = os.path.join(project_dir, "clips")
    os.makedirs(clip_dir, exist_ok=True)

    idx = 0
    for beat in doc["beats"]:
        for shot, key in shots_of(beat):
            if only and key not in only:
                idx += 1
                continue
            img = shot.get("keyframe_path")
            if not img or not os.path.exists(img):
                print(f"[{key}] no keyframe_path")
                continue
            dur = float(shot.get("dur", 5))
            frames = int(dur * FPS)
            zin = (idx % 2 == 0)   # alternate push-in / push-out for variety
            if zin:
                z = "min(zoom+0.0009,1.18)"
            else:
                z = "if(eq(on,1),1.18,max(zoom-0.0009,1.0))"
            # blurred cover background + sharp fitted card, then zoompan
            vf = (
                f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
                f"crop={W}:{H},boxblur=26:2,eq=brightness=-0.05[bg];"
                f"[0:v]scale={W}:{H}:force_original_aspect_ratio=decrease[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2,setsar=1,scale={W*2}:{H*2},"
                f"zoompan=z='{z}':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
                f"s={W}x{H}:fps={FPS}[v]"
            )
            out = os.path.join(clip_dir, f"clip_{key}.mp4")
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-i", img,
                            "-filter_complex", vf, "-map", "[v]", "-t", f"{dur}",
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", out], check=True)
            shot["clip_path"] = out
            shot.pop("clip_url", None)
            print(f"[{key}] ken-burns -> {out} ({'in' if zin else 'out'}, {dur}s)")
            idx += 1

    with open(bpath, "w", encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print("updated", bpath)


if __name__ == "__main__":
    proj = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "out", "ronaldo")
    only = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else None
    run(os.path.abspath(proj), only=only)
