#!/usr/bin/env python3
"""
A-roll assembly: mux each beat's generated visual clip with the ORIGINAL beat
segment's own audio -- never whatever audio the video model itself produced or
kept -- then concat all beats into one final.mp4.

Why remux instead of trusting the model: Omni video-edit's schema has no audio-
passthrough control at all, and the fallback models (Kling, Seedance) handle it
inconsistently. Pulling the audio straight from the untouched source segment is
the only way to guarantee the presenter's real voice stays in perfect lip-sync
regardless of which model generated that beat.

Usage: python3 aroll_assemble.py <project_dir>
"""
import json
import os
import subprocess
import sys

RES = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080),
       "4:3": (1440, 1080), "3:4": (1080, 1440)}


def ff(args):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def probe_dur(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True).stdout
    try:
        return float(out.strip())
    except ValueError:
        return 0.0


def run(project_dir):
    bpath = os.path.join(project_dir, "beats.json")
    with open(bpath) as f:
        doc = json.load(f)
    src = doc["source_video"]
    W, H = RES.get(doc.get("aspect", "9:16"), (1080, 1920))
    tmp = os.path.join(project_dir, "_seg")
    os.makedirs(tmp, exist_ok=True)

    muxed = []
    for beat in doc["beats"]:
        clip = beat.get("clip_path")
        if not clip or not os.path.exists(clip):
            print(f"[{beat['id']}] no generated clip -- skipped (missing from final)")
            continue
        audio_path = os.path.join(tmp, f"audio_{beat['id']}.aac")
        ff(["-ss", f"{beat['start']:.2f}", "-i", src, "-t", f"{beat['dur']:.2f}",
            "-vn", "-c:a", "aac", audio_path])
        vd, ad = probe_dur(clip), probe_dur(audio_path)
        d = min(vd, ad) if vd and ad else (vd or ad)
        if not d:
            print(f"[{beat['id']}] couldn't probe a duration -- skipped")
            continue
        # normalize every beat to the same canvas (models may return different
        # native sizes even at the same aspect) so the final concat is safe
        out = os.path.join(tmp, f"muxed_{beat['id']}.mp4")
        fc = (f"[0:v]scale={W}:{H}:force_original_aspect_ratio=increase,"
              f"crop={W}:{H},setsar=1,fps=24[v]")
        ff(["-i", clip, "-i", audio_path, "-filter_complex", fc, "-map", "[v]", "-map", "1:a:0",
            "-t", f"{d:.2f}", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", out])
        muxed.append(out)
        print(f"[{beat['id']}] muxed ({d:.2f}s)")

    if not muxed:
        raise SystemExit("no beats had a generated clip -- run aroll_clips.py first")

    listf = os.path.join(tmp, "concat_list.txt")
    with open(listf, "w") as f:
        for m in muxed:
            f.write(f"file '{os.path.abspath(m)}'\n")
    final = os.path.join(project_dir, "final.mp4")
    ff(["-f", "concat", "-safe", "0", "-i", listf, "-c", "copy", final])
    print("FINAL:", final, f"({len(muxed)}/{len(doc['beats'])} beats)")


if __name__ == "__main__":
    proj = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "out", "aroll-demo")
    run(os.path.abspath(proj))
