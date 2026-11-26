#!/usr/bin/env python3
"""
motion.py — local keyframe animation engine for motion-collage videos.

The core the playbook is built on: each extracted element is a Layer with a
keyframe track (fly-in / back-overshoot / bounce / slap) plus sway+pulse
"breathing"; procedural VFX (starburst, confetti) and a camera (zoom + impact
shake) sit around them. Frames are drawn with Pillow and piped to ffmpeg.

This file renders ONE proof act (2008 "KING OF EUROPE") from cr7-act elements.
Usage: python3 motion.py <project_dir> [W H fps seconds]
"""
import json
import math
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter

# ----------------------------------------------------------------- easing
def ease(e, p):
    p = max(0.0, min(1.0, p))
    if e == "linear": return p
    if e == "smooth": return p * p * (3 - 2 * p)
    if e == "in":     return p * p
    if e == "out":    return 1 - (1 - p) ** 2
    if e == "back":                              # settle with slight overshoot
        s = 1.70158
        q = p - 1
        return 1 + (s + 1) * q ** 3 + s * q ** 2
    if e == "bounce":                            # drop-in bounce
        if p < 1 / 2.75:  return 7.5625 * p * p
        if p < 2 / 2.75:  p -= 1.5 / 2.75; return 7.5625 * p * p + 0.75
        if p < 2.5 / 2.75: p -= 2.25 / 2.75; return 7.5625 * p * p + 0.9375
        p -= 2.625 / 2.75; return 7.5625 * p * p + 0.984375
    return p


class Layer:
    """img path + keyframe track. key = dict(t,x,y,s,r,a,e). x,y = center."""
    def __init__(self, img, keys, sway=0.0, pulse=0.0, shadow=True, z=0):
        self.im = Image.open(img).convert("RGBA")
        self.keys = sorted(keys, key=lambda k: k["t"])
        self.sway, self.pulse, self.shadow, self.z = sway, pulse, shadow, z

    def state(self, t):
        ks = self.keys
        if t <= ks[0]["t"]:
            k = ks[0]; return k["x"], k["y"], k["s"], k.get("r", 0), k.get("a", 1)
        if t >= ks[-1]["t"]:
            k = ks[-1]; return k["x"], k["y"], k["s"], k.get("r", 0), k.get("a", 1)
        for i in range(len(ks) - 1):
            a, b = ks[i], ks[i + 1]
            if a["t"] <= t <= b["t"]:
                p = (t - a["t"]) / (b["t"] - a["t"])
                q = ease(b.get("e", "smooth"), p)
                lerp = lambda u, v: u + (v - u) * q
                return (lerp(a["x"], b["x"]), lerp(a["y"], b["y"]), lerp(a["s"], b["s"]),
                        lerp(a.get("r", 0), b.get("r", 0)), lerp(a.get("a", 1), b.get("a", 1)))
        return ks[-1]["x"], ks[-1]["y"], ks[-1]["s"], 0, 1

    def draw(self, canvas, t):
        x, y, s, r, a = self.state(t)
        if a <= 0.01 or s <= 0.01:
            return
        # breathing
        s *= 1 + self.pulse * math.sin(t * 2.1)
        r += self.sway * math.sin(t * 1.3)
        w, h = max(1, int(self.im.width * s)), max(1, int(self.im.height * s))
        im = self.im.resize((w, h), Image.LANCZOS)
        if r:
            im = im.rotate(r, expand=True, resample=Image.BICUBIC)
        if a < 1:
            al = im.split()[3].point(lambda v: int(v * a))
            im.putalpha(al)
        px, py = int(x - im.width / 2), int(y - im.height / 2)
        if self.shadow:
            sh = Image.new("RGBA", im.size, (0, 0, 0, 0))
            sh.paste((0, 0, 0, 130), (0, 0), im.split()[3])
            sh = sh.filter(ImageFilter.GaussianBlur(9))
            canvas.alpha_composite(sh, (px + 10, py + 16))
        canvas.alpha_composite(im, (px, py))


# ------------------------------------------------------ keyframe helpers
def fly_in(t0, x, y, W, H, frm="R", spin=8, dur=0.7, s=1.0):
    off = {"R": (W + 400, y), "L": (-400, y), "T": (x, -400), "B": (x, H + 400)}[frm]
    return [dict(t=t0, x=off[0], y=off[1], s=s, r=spin, a=0, e="out"),
            dict(t=t0 + dur, x=x, y=y, s=s, r=0, a=1, e="back")]


def slap(t0, x, y, s=1.0, dur=0.25):
    return [dict(t=t0, x=x, y=y, s=s * 1.5, r=0, a=0, e="out"),
            dict(t=t0 + dur, x=x, y=y, s=s, r=0, a=1, e="back")]


def drop(t0, x, y, H, s=1.0, dur=0.8):
    return [dict(t=t0, x=x, y=-300, s=s, r=0, a=0, e="linear"),
            dict(t=t0 + 0.1, x=x, y=-300, s=s, r=0, a=1, e="linear"),
            dict(t=t0 + dur, x=x, y=y, s=s, r=0, a=1, e="bounce")]


def pop_settle(t0, x, y, s=1.0, dur=0.5, spin=6):
    """Focus-pop in place: element appears LARGER and fully opaque (so it covers
    its own copy on a full backdrop -> no ghost, no dimming needed), then settles
    to size. Scale eases only downward to 1.0 (never below) so the copy stays hidden."""
    return [dict(t=t0, x=x, y=y, s=s * 1.35, r=spin, a=0, e="out"),
            dict(t=t0 + 0.03, x=x, y=y, s=s * 1.35, r=spin, a=1, e="out"),
            dict(t=t0 + dur, x=x, y=y, s=s, r=0, a=1, e="out")]


# ------------------------------------------------------ procedural VFX
def starburst(canvas, cx, cy, t, R=760, rays=28, col=(240, 200, 70)):
    lay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    rot = t * 18
    for i in range(rays):
        a0 = math.radians(rot + i * 360 / rays)
        a1 = math.radians(rot + (i + 0.5) * 360 / rays)
        d.polygon([(cx, cy),
                   (cx + R * math.cos(a0), cy + R * math.sin(a0)),
                   (cx + R * math.cos(a1), cy + R * math.sin(a1))], fill=col + (60,))
    canvas.alpha_composite(lay)


class Confetti:
    def __init__(self, W, H, n=46, seed=7):
        import random
        self.r = random.Random(seed); self.W, self.H = W, H
        self.p = [dict(x=self.r.uniform(0, W), y=self.r.uniform(-H, H),
                       vy=self.r.uniform(60, 150), vx=self.r.uniform(-30, 30),
                       w=self.r.randint(7, 16), h=self.r.randint(9, 22),
                       rot=self.r.uniform(0, 360), vr=self.r.uniform(-120, 120),
                       c=self.r.choice([(212, 175, 55), (240, 240, 235), (200, 50, 40),
                                        (40, 110, 110), (230, 205, 110)])) for _ in range(n)]

    def draw(self, canvas, t, dt):
        lay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        for p in self.p:
            p["y"] += p["vy"] * dt; p["x"] += p["vx"] * dt + 6 * math.sin(t + p["w"])
            p["rot"] += p["vr"] * dt
            if p["y"] > self.H + 20:
                p["y"] = -20; p["x"] = self.r.uniform(0, self.W) if hasattr(self, "r") else p["x"]
            chip = Image.new("RGBA", (p["w"], p["h"]), p["c"] + (235,))
            chip = chip.rotate(p["rot"], expand=True)
            lay.alpha_composite(chip, (int(p["x"]), int(p["y"])))
        canvas.alpha_composite(lay)


# ------------------------------------------------------------- 2008 act
def build_act(project_dir, W, H):
    """Elements fly back to their ORIGINAL positions on the card (canvas 3:4),
    so the assembled frame reconstructs the original poster."""
    els = {e["name"]: e["file"] for e in
           json.load(open(os.path.join(project_dir, "elements_spec.json"), encoding="utf-8"))["elements"]}
    S = W / 768.0                    # card is 768 wide; scale elements to canvas
    # original centers on card * S  ->  (x, y)
    P = {"crest": (255, 238), "seven": (215, 575), "ronaldo": (666, 647),
         "trophy": (863, 889), "king": (249, 966), "y2008": (839, 1249)}
    # draw order = original z (trophy sits in front of ronaldo, etc.)
    # off-screen fly-in back to each element's ORIGINAL position; pale placeholders
    # on the backdrop mark the landing zones (no dark boxes, no ghost).
    return [
        Layer(els["crest"],   fly_in(0.15, *P["crest"], W, H, "T", spin=-6, dur=0.6, s=S), sway=0.6),
        Layer(els["seven"],   fly_in(0.30, *P["seven"], W, H, "L", spin=-8, dur=0.6, s=S), sway=1.0),
        Layer(els["ronaldo"], fly_in(0.50, *P["ronaldo"], W, H, "R", spin=4, dur=0.7, s=S),
              sway=0.4, pulse=0.004),
        Layer(els["trophy"],  drop(0.85, *P["trophy"], H, s=S), sway=0.8),
        Layer(els["king"],    fly_in(1.10, *P["king"], W, H, "L", spin=-5, dur=0.6, s=S), sway=0.6),
        Layer(els["y2008"],   fly_in(1.40, *P["y2008"], W, H, "R", spin=8, dur=0.5, s=S)),
    ]


def cam(t, T):
    z = 1.0 + 0.06 * (t / T)                     # slow push-in
    sx = sy = 0.0
    for hit in (0.6, 1.25, 1.7):                 # impact shakes on entries
        if t >= hit:
            d = t - hit
            amp = 22 * math.exp(-8 * d)
            sx += amp * math.sin(d * 60); sy += amp * math.cos(d * 55)
    return z, sx, sy


def render(project_dir, W=1080, H=1440, fps=24, secs=5.5):
    backdrop = Image.open(os.path.join(project_dir, "base_backdrop.png")).convert("RGBA").resize((W, H))
    layers = build_act(project_dir, W, H)
    conf = Confetti(W, H, n=30)
    out = os.path.join(project_dir, "act.mp4")
    p = subprocess.Popen(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
         "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
         "-c:v", "libx264", "-pix_fmt", "yuv420p", out], stdin=subprocess.PIPE)
    n = int(secs * fps); dt = 1.0 / fps
    for f in range(n):
        t = f * dt
        cv = backdrop.copy()                                   # original card as base
        for L in layers:
            L.draw(cv, t)
        conf.draw(cv, t, dt)
        z, sx, sy = cam(t, secs)
        frame = cv.convert("RGB")
        zw, zh = int(W * z), int(H * z)
        frame = frame.resize((zw, zh), Image.LANCZOS)
        cx, cy = (zw - W) // 2 + int(sx), (zh - H) // 2 + int(sy)
        cx = max(0, min(zw - W, cx)); cy = max(0, min(zh - H, cy))
        frame = frame.crop((cx, cy, cx + W, cy + H))
        p.stdin.write(frame.tobytes())
    p.stdin.close(); p.wait()
    print("FINAL:", out, f"({n}f {W}x{H})")


if __name__ == "__main__":
    proj = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(__file__), "..", "out", "cr7-act")
    render(os.path.abspath(proj))
