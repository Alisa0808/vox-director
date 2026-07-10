#!/usr/bin/env python3
"""
Audio stage: per-beat narration (one consistent voice) + one instrumental BGM.

Narration uses xai/tts-v1 (a real multilingual TTS: named `voice_id` + language),
so every beat is spoken in the same voice — this sidesteps Omni's clip-to-clip
voice drift. Seed-Audio was tried and dropped: as a general *sound* model it gave
wildly inconsistent narration lengths unless a speaker is pinned (see VOICE_MODEL).

Usage: python3 audio.py <project_dir>   (default: out/tang-30s)
"""
import json
import os
import subprocess
import sys

from provider import get_provider, run_jobs

# xai/tts-v1 is a clean, predictable multilingual TTS (named voices + language
# select). Seed-Audio is a general *sound* model that injects pauses/SFX and
# gave wildly inconsistent narration lengths, so we use a real TTS here.
VOICE_MODEL = "xai/tts-v1"
MUSIC_MODEL = "minimax/music-2.6"


def probe_dur(path: str) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True).stdout
    try:
        return float(out.strip())
    except ValueError:
        return 0.0


def run(project_dir: str):
    bpath = os.path.join(project_dir, "beats.json")
    with open(bpath) as f:
        doc = json.load(f)
    adir = os.path.join(project_dir, "audio")
    os.makedirs(adir, exist_ok=True)

    prov = get_provider(doc.get("provider"))
    voice = doc.get("voice", {})
    voice_id = voice.get("voice_id", "leo")     # named male documentary-ish voice
    language = voice.get("language", doc.get("language", "en"))
    speed = float(voice.get("speed", 1.0))

    specs = {}
    for beat in doc["beats"]:
        specs[f"narr_{beat['id']}"] = (lambda t=beat["narration"]: prov.submit_audio(
            VOICE_MODEL, text=t, language=language, voice_id=voice_id,
            codec="mp3", sample_rate=44100, speed=speed))

    # BGM: only generate if we don't already have one (it's slow + costs more).
    bgm_path = os.path.join(adir, "bgm.mp3")
    if not os.path.exists(bgm_path):
        music_prompt = doc.get("music", "cinematic majestic traditional Chinese guzheng erhu, warm")
        specs["bgm"] = (lambda mp=music_prompt: prov.submit_audio(
            MUSIC_MODEL, prompt=mp, is_instrumental=True, format="mp3"))
    else:
        print(f"[bgm] reuse existing {bgm_path}")

    done = run_jobs(prov, specs, poll_s=4, stall_s=150, max_retries=2, deadline_s=600)

    # download + record
    for beat in doc["beats"]:
        url = done.get(f"narr_{beat['id']}")
        if url:
            dest = os.path.join(adir, f"narr_{beat['id']}.mp3")
            prov.download(url, dest)
            beat["narration_audio"] = dest
            beat["narration_dur"] = round(probe_dur(dest), 2)
            print(f"[narr {beat['id']}] {beat['narration_dur']}s -> {dest}")
    bgm_url = done.get("bgm")
    if bgm_url:
        bgm = os.path.join(adir, "bgm.mp3")
        prov.download(bgm_url, bgm)
        doc["bgm_path"] = bgm
        doc["bgm_dur"] = round(probe_dur(bgm), 2)
        print(f"[bgm] {doc['bgm_dur']}s -> {bgm}")

    with open(bpath, "w") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print("updated", bpath)


if __name__ == "__main__":
    proj = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "out", "tang-30s")
    run(os.path.abspath(proj))
