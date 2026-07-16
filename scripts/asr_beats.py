#!/usr/bin/env python3
"""
ASR bridge (A-roll only): turn a raw talking-head recording's own baked-in audio
into a beats.json skeleton, so A-roll mode can cut and re-style it beat-by-beat
without anyone hand-timing the source video.

Unlike B-roll (Claude authors `narration` text up front, audio.py then synthesizes
it), A-roll starts from audio that already exists: the presenter already spoke it
on camera. So the direction is reversed -- transcribe first, segment the
transcript into natural beats by sentence-ending punctuation and pause gaps, and
write out beat time ranges + text. This draft is still the same "first mandatory
approval gate" as the B-roll beat map (see SKILL.md step 1): review/edit it
(theme, content_beats, video_model) before running aroll_clips.py.

Usage:
  python3 asr_beats.py <project_dir> <source_video_or_audio> [--language en]
                       [--keyterm name1,name2] [--max-beat-dur 9.5]
"""
import argparse
import json
import os
import subprocess
import sys

import atlas_cloud
from provider import get_provider

# Both Omni video-edit and Kling video-edit cap a single call at 10s; leave headroom
# so a beat that lands right on the limit doesn't get rejected for being 10.0s exactly.
MAX_BEAT_DUR = 9.5
MIN_BEAT_DUR = 2.0
PAUSE_GAP_S = 0.35            # a gap this long between words reads as a natural pause
SENTENCE_END = (".", "!", "?")


def probe_dims(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0",
                          "-show_entries", "stream=width,height", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout.strip()
    if not out:
        return None
    w, h = (int(x) for x in out.split(",")[:2])
    return w, h


def nearest_named_aspect(w, h):
    """Snap a raw pixel size to the nearest of the common named ratios, purely so
    beats.json carries a human-readable target -- the real routing/approximation
    decision still happens in styles.resolve_video_aspect at generation time."""
    named = {"16:9": 16 / 9, "9:16": 9 / 16, "1:1": 1.0, "4:3": 4 / 3, "3:4": 3 / 4}
    ratio = w / h
    return min(named, key=lambda k: abs(named[k] - ratio))


def extract_audio(src, dest):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-vn",
                    "-acodec", "libmp3lame", "-q:a", "2", dest], check=True)


def segment_words(words, max_dur=MAX_BEAT_DUR, min_dur=MIN_BEAT_DUR, pause_gap=PAUSE_GAP_S):
    """Group word-level ASR timestamps into beats. A beat ends at a sentence-ending
    word once it's at least min_dur long, or at a pause gap, or is force-cut before
    max_dur so no single call ever exceeds a video model's per-call duration cap.
    Trailing fragments shorter than min_dur are merged into the previous beat."""
    beats, cur = [], []

    def flush():
        if not cur:
            return
        beats.append({
            "start": round(cur[0]["start"], 2),
            "end": round(cur[-1]["end"], 2),
            "text": " ".join(w["text"] for w in cur),
        })
        cur.clear()

    for i, w in enumerate(words):
        cur.append(w)
        dur = w["end"] - cur[0]["start"]
        is_last = i == len(words) - 1
        gap_next = (words[i + 1]["start"] - w["end"]) if not is_last else None
        sentence_end = w["text"].rstrip().endswith(SENTENCE_END)
        if is_last:
            flush()
        elif dur >= max_dur:                          # force cut -- never exceed the model cap
            flush()
        elif dur >= min_dur and (sentence_end or (gap_next is not None and gap_next >= pause_gap)):
            flush()

    # merge any too-short trailing beat into its predecessor rather than emitting a
    # sub-min_dur clip that's awkward to generate/cut on its own
    merged = []
    for b in beats:
        if merged and (b["end"] - b["start"]) < min_dur:
            merged[-1]["end"] = b["end"]
            merged[-1]["text"] += " " + b["text"]
        else:
            merged.append(b)
    return merged


def run(project_dir, source, language=None, keyterm=None, max_beat_dur=MAX_BEAT_DUR,
        provider_name=None):
    os.makedirs(project_dir, exist_ok=True)
    bpath = os.path.join(project_dir, "beats.json")

    dims = probe_dims(source)
    aspect = nearest_named_aspect(*dims) if dims else "9:16"

    audio_path = source
    if not source.lower().endswith((".mp3", ".wav", ".m4a", ".flac", ".ogg")):
        audio_path = os.path.join(project_dir, "asr_audio.mp3")
        print(f"extracting audio -> {audio_path}")
        extract_audio(source, audio_path)

    prov = get_provider(provider_name)
    print("uploading audio for ASR...")
    audio_url = prov.upload(audio_path)
    print("transcribing (xai/stt-v1)...")
    result = atlas_cloud.transcribe(audio_url, language=language,
                                    keyterm=keyterm.split(",") if keyterm else None)
    words = result.get("words", [])
    if not words:
        raise SystemExit("ASR returned no word timestamps -- check the source audio")

    segments = segment_words(words, max_dur=max_beat_dur)
    beats = [{
        "id": i + 1,
        "start": s["start"],
        "end": s["end"],
        "dur": round(s["end"] - s["start"], 2),
        "text": s["text"],
        "content_beats": "",   # optional: fill in per-beat sticker/stamp/overlay ideas
    } for i, s in enumerate(segments)]

    doc = {
        "project": os.path.basename(project_dir.rstrip("/")),
        "mode": "aroll",
        "source_video": os.path.abspath(source),
        "language": result.get("language") or language or "en",
        "aspect": aspect,
        "style": "collage",
        "theme": None,                                    # fill in after a style bake-off
        "video_model": "google/gemini-omni-flash/video-edit",
        "video_model_fallback": "bytedance/seedance-2.0/reference-to-video",
        "transcript": result.get("text", ""),
        "beats": beats,
    }
    with open(bpath, "w") as f:
        json.dump(doc, f, ensure_ascii=False, indent=2)
    print(f"wrote {len(beats)} beats -> {bpath}")
    print("review/edit theme + content_beats, then run aroll_clips.py "
          "(this draft is the approval gate -- don't generate off it unreviewed).")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("project_dir")
    ap.add_argument("source", help="raw talking-head video or audio file")
    ap.add_argument("--language", default=None)
    ap.add_argument("--keyterm", default=None, help="comma-separated names/terms to bias ASR toward")
    ap.add_argument("--max-beat-dur", type=float, default=MAX_BEAT_DUR)
    ap.add_argument("--provider", default=None)
    a = ap.parse_args()
    run(os.path.abspath(a.project_dir), a.source, language=a.language, keyterm=a.keyterm,
        max_beat_dur=a.max_beat_dur, provider_name=a.provider)
