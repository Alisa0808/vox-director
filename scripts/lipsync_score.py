#!/usr/bin/env python3
"""
Score lip-sync objectively (optional QA for host mode; needs numpy + Pillow).

Correlates mouth-region frame-difference energy against the audio envelope at 25 fps and
reports two numbers per video:

  best lag   the timing check. A non-zero lag means a constant offset: a TIMING bug you can
             fix (wrong audio, padding, a stray time shift).
  corr@0     the fidelity check. Low correlation at zero lag means the mouth moves at the right
             times but its shape does not follow the phonemes: a MODEL limit that prompts
             cannot fix; only a different model can.

Same metric, same plate, same audio for every video, so the numbers are comparable across
models. Measured on one green plate (2026-07-30): InfiniteTalk 0.503, Kling 0.460, OmniHuman
0.422, Seedance 0.246, all at ~0 lag once the audio was handled correctly.

The mouth box is a fraction of the frame, (x, y, w, h). The default is calibrated to the
standard host layout; if the presenter's size or position differs, find the mouth on a frame
and pass --mouth.

Usage: python3 lipsync_score.py <audio.mp3> <video.mp4> [more.mp4 ...] [--mouth x,y,w,h]
"""
import glob
import os
import shutil
import subprocess
import sys
import tempfile

FPS = 25


def _np():
    try:
        import numpy as np
        from PIL import Image
    except ImportError:
        sys.exit("lipsync_score.py needs numpy and Pillow: pip install numpy pillow")
    return np, Image


def envelope(audio, n, np):
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", audio, "-ac", "1", "-ar", "16000",
                          "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(out, dtype=np.int16).astype(float)
    hop = 16000 // FPS
    return np.array([np.sqrt((x[i * hop:(i + 1) * hop] ** 2).mean() + 1e-9)
                     for i in range(min(n, len(x) // hop))])


def mouth_motion(video, box, np, Image):
    x, y, w, h = box
    crop = f"crop=iw*{w}:ih*{h}:iw*{x}:ih*{y}"
    tmp = tempfile.mkdtemp(prefix="lipsync_")
    try:
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", video, "-vf",
                        f"{crop},scale=112:-1,fps={FPS},format=gray",
                        os.path.join(tmp, "f_%04d.png")], check=True)
        frames = [np.asarray(Image.open(p), dtype=float)
                  for p in sorted(glob.glob(os.path.join(tmp, "f_*.png")))]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return np.array([0.0] + [np.abs(frames[i] - frames[i - 1]).mean()
                             for i in range(1, len(frames))])


def _z(a, np):
    a = a - a.mean()
    s = a.std()
    return a / s if s > 1e-9 else a


def score(video, audio, box):
    np, Image = _np()
    m = mouth_motion(video, box, np, Image)
    e = envelope(audio, len(m), np)
    n = min(len(m), len(e))
    o, ee = _z(m[:n], np), _z(e[:n], np)
    best = (0, -9.0)
    for lag in range(-25, 26):
        if lag < 0:
            a, b = o[-lag:], ee[:len(ee) + lag]
        elif lag == 0:
            a, b = o, ee
        else:
            a, b = o[:len(o) - lag], ee[lag:]
        k = min(len(a), len(b))
        c = float((a[:k] * b[:k]).mean())
        if c > best[1]:
            best = (lag, c)
    return best[0] / FPS, best[1], float((o * ee).mean()), len(m) / FPS


if __name__ == "__main__":
    argv = sys.argv[1:]
    box = None
    if "--mouth" in argv:
        i = argv.index("--mouth")
        box = tuple(float(v) for v in argv[i + 1].split(","))
        del argv[i:i + 2]
    if len(argv) < 2:
        sys.exit(__doc__)
    if box is None:
        from host import HOST_LAYOUTS
        box = HOST_LAYOUTS["16:9"]["mouth_box"]
    audio = argv[0]
    print(f"{'video':18} {'dur':>6} {'corr@0':>8} {'best lag':>9} {'best corr':>10}")
    for v in argv[1:]:
        lag, bc, c0, dur = score(v, audio, box)
        print(f"{os.path.basename(v)[:-4][:18]:18} {dur:6.2f} {c0:+8.3f} {lag:+9.3f}s {bc:+10.3f}")
