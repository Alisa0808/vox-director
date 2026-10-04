#!/usr/bin/env python3
"""
Host stage 2: animate both plates, adopt the presenter's own audio, key and stack.

  person plate -> Seedance 2.0 reference-to-video, driven by the beat's narration
  world plate  -> Gemini Omni image-to-video (flat paper-collage motion, camera locked)
  composite    -> chroma-key the green out of the person clip, overlay on the world clip

Three rules in here each came from a failed run (details: references/host-mode.md):
  1. The audio handed to Seedance is padded to EXACTLY the video length.
  2. The beat's audio then becomes Seedance's OWN output track, not the original narration —
     Seedance re-times the reference audio, so laying the original back over the video builds
     in a ~0.4s error that no constant shift can remove.
  3. The finished shot is never time-stretched (assemble.py honours kind == "host").

This spends money. Without --yes it only prints the plan and an estimate; show that to the
user, and re-run with --yes once they agree.

Usage: python3 host_clips.py <project_dir> [only_ids] [--yes] [--redo]
       --redo regenerates the videos even if clips already exist (re-composite is always free)
"""
import json
import os
import subprocess
import sys

from host import (CHROMA, DEFAULT_WORLD_MOTION, PERSON_VIDEO_MODEL, PERSON_VIDEO_PROMPT,
                  WORLD_VIDEO_MODEL, WORLD_VIDEO_PROMPT, estimate, host_cfg, layout_for,
                  probe_dur, reference_audio, validate, video_seconds)
from provider import get_provider, run_jobs

FPS = 24
RES = {"16:9": (1920, 1080)}


def sh(args):
    subprocess.run(args, check=True)


def pad_audio(src, dest, seconds):
    """Pad with trailing silence to EXACTLY `seconds`.

    Seedance spreads the lip motion over the whole requested video length instead of stopping
    when the audio does: 7.04s of speech in an 8s clip came back ~14% slow, the mouth stayed
    open after the speech ended, and the sync drifted the longer the shot ran.
    """
    sh(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-af", "apad", "-t", f"{seconds}",
        "-c:a", "libmp3lame", "-q:a", "2", dest])
    return dest


def adopt_model_audio(plate, dest, level_db=-18.0):
    """Extract the presenter clip's own audio and level-match it (content is verbatim)."""
    sh(["ffmpeg", "-y", "-loglevel", "error", "-i", plate, "-vn",
        "-af", f"loudnorm=I={level_db}:TP=-2:LRA=9", "-ac", "1", "-ar", "44100",
        "-c:a", "libmp3lame", "-q:a", "2", dest])
    return dest


def composite(person, world, dest, size, similarity=0.20, blend=0.06):
    """Key the flat green out of the person clip and lay it over the world clip.

    Both plates share one framing, so the overlay is at 0:0 with no repositioning. No time
    shift is applied: with the model's own audio adopted, the measured offset is ~0 and any
    shift would only break it.
    """
    w, h = size
    fc = (f"[0:v]scale={w}:{h},fps={FPS},setsar=1[bg];"
          f"[1:v]scale={w}:{h},fps={FPS},setsar=1,"
          f"colorkey={CHROMA}:{similarity}:{blend},despill=type=green:mix=0.5[fg];"
          f"[bg][fg]overlay=0:0:format=auto,format=yuv420p[v]")
    sh(["ffmpeg", "-y", "-loglevel", "error", "-i", world, "-i", person, "-filter_complex", fc,
        "-map", "[v]", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", dest])


def run(project_dir, only=None, confirmed=False, redo=False):
    bpath = os.path.join(project_dir, "beats.json")
    with open(bpath) as f:
        doc = json.load(f)
    shots = [t for t in validate(doc, need_audio=True) if not only or t[2] in only]
    aspect = doc.get("aspect", "16:9")
    layout = layout_for(aspect)
    size = RES[aspect]
    cfg = host_cfg(doc)
    plates_dir = os.path.join(project_dir, "clips", "plates")
    audio_dir = os.path.join(project_dir, "audio", "host")
    for d in (plates_dir, audio_dir):
        os.makedirs(d, exist_ok=True)

    missing = [k for _, s, k in shots if not (s.get("person_plate_url") and s.get("world_plate_url"))]
    if missing:
        sys.exit(f"no plates for {', '.join(missing)} — run host_plates.py first")

    # ---- plan + cost gate ----
    seconds = {k: video_seconds(probe_dur(reference_audio(b))) for b, _, k in shots}

    def need(shot, field):
        """Generate this clip unless it is already on disk (--redo forces)."""
        return redo or not os.path.exists(shot.get(f"{field}_path") or "")

    person_s = {k: seconds[k] for _, s, k in shots if need(s, "person_clip")}
    world_s = {k: seconds[k] for _, s, k in shots if need(s, "world_clip")}
    print("host clips plan:")
    for _, _, k in shots:
        what = [n for n, d in (("person", person_s), ("world", world_s)) if k in d]
        print(f"  [{k}] {seconds[k]}s clip: " + (f"generate {' + '.join(what)}" if what
                                              else "reuse existing clips (re-composite only)"))
    if person_s or world_s:
        lines, total = estimate(person_s, world_s)
        print("estimate (prices from 2026-07-30 official pages — verify):")
        print("\n".join(lines))
        print(f"  TOTAL ~ ${total:.2f}")
        if not confirmed:
            print("\nNothing submitted. Show this estimate to the user; re-run with --yes to go.")
            return

    prov = get_provider(doc.get("provider"))
    specs, meta = {}, {}
    for beat, shot, key in shots:
        vdur = seconds[key]
        shot["plate_dur"] = vdur
        feel = f"Tone: {beat.get('feel', 'warm and clear')}."
        if key in person_s:
            padded = pad_audio(reference_audio(beat), os.path.join(audio_dir, f"ref_{key}.mp3"),
                               vdur)
            audio_url = prov.upload(padded)
            prompt = PERSON_VIDEO_PROMPT.format(
                subject=cfg["subject"], side=layout["side"], outfit_clause=cfg["outfit_clause"],
                feel=feel)
            shot["person_video_prompt"] = prompt
            specs[f"{key}-person"] = (lambda p=shot["person_plate_url"], a=audio_url, v=vdur,
                                      t=prompt: prov.submit_video(
                PERSON_VIDEO_MODEL, t, reference_images=[p], reference_audios=[a], duration=v,
                ratio=aspect, resolution="720p", generate_audio=True, watermark=False,
                bitrate_mode="standard"))
            meta[f"{key}-person"] = (shot, "person_clip")
        if key in world_s:
            prompt = WORLD_VIDEO_PROMPT.format(
                element_motion=shot.get("element_motion") or DEFAULT_WORLD_MOTION,
                side=layout["side"], feel=feel)
            shot["world_video_prompt"] = prompt
            specs[f"{key}-world"] = (lambda p=shot["world_plate_url"], v=vdur,
                                     t=prompt: prov.submit_video(
                WORLD_VIDEO_MODEL, t, image=p, duration=v, aspect_ratio=aspect,
                resolution="720p"))
            meta[f"{key}-world"] = (shot, "world_clip")

    done = run_jobs(prov, specs, poll_s=5, stall_s=300, max_retries=2, deadline_s=1500)
    for k, url in done.items():
        if not url:
            print(f"[{k}] FAILED")
            continue
        shot, field = meta[k]
        dest = os.path.join(plates_dir, f"{k}.mp4")
        prov.download(url, dest)
        shot[f"{field}_url"], shot[f"{field}_path"] = url, dest
        print(f"[{k}] saved {dest} ({probe_dur(dest):.2f}s)")

    # ---- adopt the presenter's own audio, then key + stack ----
    for beat, shot, key in shots:
        pc, wc = shot.get("person_clip_path"), shot.get("world_clip_path")
        if not (pc and wc and os.path.exists(pc) and os.path.exists(wc)):
            print(f"[{key}] missing a clip — skipping composite")
            continue
        own = os.path.join(audio_dir, f"own_{key}.mp3")
        adopt_model_audio(pc, own)
        original = reference_audio(beat)
        beat["narration_audio_reference"] = original
        beat["narration_audio"] = beat["host_own_audio"] = own
        beat["narration_dur"] = round(probe_dur(own), 3)
        beat.pop("narration_audio_url", None)
        dest = os.path.join(project_dir, "clips", f"clip_{key}.mp4")
        composite(pc, wc, dest, size)
        shot["clip_path"] = dest
        shot["dur"] = round(probe_dur(dest), 3)       # assemble keeps host shots at this length
        shot.pop("clip_url", None)
        print(f"[{key}] composited -> {dest} ({shot['dur']}s, audio {beat['narration_dur']}s)")

    with open(bpath, "w") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print("updated", bpath)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit("usage: python3 host_clips.py <project_dir> [only_ids] [--yes] [--redo]")
    only = set(args[1].split(",")) if len(args) > 1 else None
    run(os.path.abspath(args[0]), only, confirmed="--yes" in sys.argv, redo="--redo" in sys.argv)
