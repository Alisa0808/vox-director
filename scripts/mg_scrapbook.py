#!/usr/bin/env python3
"""
Scrapbook MG assembly (with whip cuts + ending card layout):
  - each (Kling) card clip = a tilted card on a cream desk
  - beats joined with fast whip (xfade slide) transitions
  - an ending shot where all cards settle into a scrapbook layout + title
  - drifting confetti over the whole piece; narration + ducked music + captions

Assumes one clip per beat (beats have no multi-shot). Needs assets/confetti.mp4.
Usage: python3 mg_scrapbook.py <project_dir>
"""
import json
import math
import os
import subprocess
import sys

from safety import validate_project
import text_overlay

FPS, TAIL, WHIP = 24, 0.5, 0.3
END_DUR = 4.5
RES = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080), "3:4": (1080, 1440)}
CREAM = "0xE9E1D0"
TILT = [-2.5, 2.0, -2.0, 2.5, -1.5, 2.2]
TRANS = ["slideright", "slideleft", "slideup", "slideright", "slideleft"]
END_TITLE = "CRISTIANO — FOREVER"
END_SUB = "FIVE CHAPTERS · ONE No.7"


def ff(a):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *a], check=True)


def probe_dur(p):
    o = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", p], capture_output=True, text=True).stdout
    try:
        return float(o.strip())
    except ValueError:
        return 0.0


def build_seg(clip, dur, tilt_deg, W, H, out):
    cd = probe_dur(clip)
    factor = dur / cd if cd > 0 else 1.0
    pre = f"setpts={factor:.4f}*PTS," if factor > 1.02 else ""
    rad = math.radians(tilt_deg)
    fc = (f"color=c={CREAM}:s={W}x{H}:d={dur}:r={FPS},format=rgb24[bg];"
          f"[0:v]{pre}scale={int(W*0.84)}:-1:flags=lanczos,format=rgba,"
          f"rotate={rad:.4f}:c=none:ow=rotw({rad:.4f}):oh=roth({rad:.4f}),fps={FPS}[c];"
          f"[bg][c]overlay=(W-w)/2:(H-h)/2,setsar=1,format=yuv420p,"
          f"tpad=stop_mode=clone:stop_duration=1[v]")
    ff(["-i", clip, "-filter_complex", fc, "-map", "[v]", "-t", f"{dur}",
        "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", out])


def build_ending(cards, W, H, out, tmp):
    title = text_overlay.render_title(END_TITLE, os.path.join(tmp, "title.png"), W, H, END_SUB)
    Wm = int(W * 0.34)
    pos = [(70, 440, -6), (600, 370, 5), (95, 980, 4), (610, 960, -5), (345, 1380, 3)]
    inputs = ["-f", "lavfi", "-i", f"color=c={CREAM}:s={W}x{H}:d={END_DUR}:r={FPS}"]
    for c in cards:
        inputs += ["-i", c]
    inputs += ["-i", title]
    parts = ["[0:v]format=rgb24[bg]"]
    prev = "[bg]"
    for i, (x, y, deg) in enumerate(pos):
        rad = math.radians(deg)
        parts.append(f"[{i+1}:v]scale={Wm}:-1,format=rgba,"
                     f"rotate={rad:.4f}:c=none:ow=rotw({rad:.4f}):oh=roth({rad:.4f})[k{i}]")
        parts.append(f"{prev}[k{i}]overlay={x}:{y}:eof_action=repeat[o{i}]")
        prev = f"[o{i}]"
    parts.append(f"{prev}[{len(cards)+1}:v]overlay=0:0:eof_action=repeat,setsar=1,format=yuv420p[v]")
    ff([*inputs, "-filter_complex", ";".join(parts), "-map", "[v]", "-t", f"{END_DUR}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", out])


def run(project_dir):
    with open(os.path.join(project_dir, "beats.json")) as f:
        doc = json.load(f)
    validate_project(project_dir, doc)
    beats = doc["beats"]
    W, H = RES.get(doc.get("aspect", "9:16"), (1080, 1920))
    wm_text = doc.get("watermark", "Made with Atlas Cloud · vox-director")
    confetti = os.path.join(project_dir, "assets", "confetti.mp4")
    tmp = os.path.join(project_dir, "_seg"); os.makedirs(tmp, exist_ok=True)

    # 1) per-beat segments (tilted card on cream)
    seg_files, seg_durs = [], []
    for i, beat in enumerate(beats):
        shot = beat["shots"][0] if beat.get("shots") else beat
        d = max(float(shot.get("dur", 5)), float(beat.get("narration_dur", 5)) + TAIL)
        out = os.path.join(tmp, f"seg_{i:02d}.mp4")
        build_seg(shot["clip_path"], round(d, 2), TILT[i % len(TILT)], W, H, out)
        seg_files.append(out); seg_durs.append(round(d, 2))

    # ending assembly clip
    ending = os.path.join(tmp, "ending.mp4")
    build_ending([b.get("shots", [b])[0]["keyframe_path"] if b.get("shots")
                  else b["keyframe_path"] for b in beats], W, H, ending, tmp)

    clips = seg_files + [ending]
    durs = seg_durs + [END_DUR]

    # 2) whip (xfade) chain; compute each beat's start in the final timeline
    inputs = []
    for c in clips:
        inputs += ["-i", c]
    chain, prev, acc, starts = [], "[0:v]", durs[0], [0.0]
    for i in range(1, len(clips)):
        off = acc - WHIP
        lbl = f"[x{i}]"
        tr = TRANS[(i - 1) % len(TRANS)]
        chain.append(f"{prev}[{i}:v]xfade=transition={tr}:duration={WHIP}:offset={off:.3f}{lbl}")
        prev = lbl
        starts.append(off)
        acc = acc + durs[i] - WHIP
    total = round(acc, 2)
    body = os.path.join(tmp, "body_whip.mp4")
    ff([*inputs, "-filter_complex", ";".join(chain), "-map", prev,
        "-c:v", "libx264", "-pix_fmt", "yuv420p", body])

    # beat spans (only the narrated beats, not the ending)
    spans = []
    for i, beat in enumerate(beats):
        st = starts[i] + (WHIP if i > 0 else 0)
        spans.append({"start": st, "dur": seg_durs[i], "beat": beat})

    # 3) captions + wm PNGs
    caps = [text_overlay.render_caption(sp["beat"]["narration"],
            os.path.join(tmp, f"cap_{sp['beat']['id']}.png"), W, H) for sp in spans]
    wm = text_overlay.render_watermark(wm_text, os.path.join(tmp, "wm.png"), W, H)

    # 4) confetti screen-blend + captions + wm + narration/music
    nb = len(spans)
    inp = ["-i", body, "-stream_loop", "-1", "-i", confetti]
    for p in caps:
        inp += ["-i", p]
    inp += ["-i", wm]
    narr_base = 2 + nb + 1
    for sp in spans:
        inp += ["-i", sp["beat"]["narration_audio"]]
    bgm_idx = narr_base + nb
    inp += ["-i", doc["bgm_path"]]

    ch = [f"[1:v]scale={W}:{H},setpts=PTS-STARTPTS,format=gbrp[cf]",
          "[0:v]format=gbrp[bb]",
          "[bb][cf]blend=all_mode=screen:shortest=1,format=yuv420p[vb]"]
    prev = "[vb]"
    for i, sp in enumerate(spans):
        s, e = sp["start"] + 0.2, sp["start"] + sp["dur"] - 0.1
        ch.append(f"{prev}[{2+i}:v]overlay=0:0:enable='between(t,{s:.2f},{e:.2f})'[v{i+1}]")
        prev = f"[v{i+1}]"
    ch.append(f"{prev}[{2+nb}:v]overlay=0:0[v]")
    nl = []
    for i, sp in enumerate(spans):
        ch.append(f"[{narr_base+i}:a]adelay={int(sp['start']*1000)}:all=1[n{i}]"); nl.append(f"[n{i}]")
    ch.append(f"{''.join(nl)}amix=inputs={nb}:normalize=0:duration=longest,apad,atrim=0:{total}[nm]")
    ch.append("[nm]asplit=2[nA][nB]")
    ch.append(f"[{bgm_idx}:a]atrim=0:{total},volume=0.9,afade=t=out:st={max(total-2,0):.2f}:d=2[bgt]")
    ch.append("[bgt][nA]sidechaincompress=threshold=0.02:ratio=12:attack=5:release=350[bgd]")
    ch.append(f"[nB][bgd]amix=inputs=2:normalize=0:duration=longest,volume=1.4,atrim=0:{total}[a]")

    final = os.path.join(project_dir, "final_mg.mp4")
    ff([*inp, "-filter_complex", ";".join(ch), "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", final])
    print("FINAL:", final, f"(~{total}s, {len(beats)} beats + ending)")


if __name__ == "__main__":
    proj = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "out", "ronaldo")
    run(os.path.abspath(proj))
