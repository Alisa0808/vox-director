#!/usr/bin/env python3
"""
Text overlays via Pillow -> transparent PNG (this ffmpeg has no libass/drawtext,
so captions/watermark are rendered as images and composited with `overlay`).
"""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT_BOLD = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]
FONT_REG = [
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
]


def _font(paths, size):
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=fnt) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def accent_color(image_path, default=(214, 64, 42)):
    """Sample a vibrant color from a keyframe so the caption keyline travels with
    each film's palette (Mexican -> pink/teal, Tang -> vermilion...). Fallback default."""
    try:
        im = Image.open(image_path).convert("RGB").resize((80, 80)).quantize(colors=24).convert("RGB")
    except Exception:
        return default
    best, best_score = None, -1.0
    for count, (r, g, b) in (im.getcolors(80 * 80) or []):
        mx, mn = max(r, g, b), min(r, g, b)
        if mx == 0:
            continue
        sat, val = (mx - mn) / mx, mx / 255.0
        if sat < 0.45 or val < 0.35 or val > 0.92:   # skip washed-out / too dark / too light
            continue
        score = sat * val * (count ** 0.3)
        if score > best_score:
            best, best_score = (r, g, b), score
    return best or default


def render_caption(text, out_path, W=1920, H=1080, margin_v=None, accent=None):
    """Cut-out paper caption: cream letters + dark-ink edge + soft shadow, NO band
    (never covers the video). `accent` (RGB) adds a per-beat colored keyline. Small
    size (like the old captions) so it doesn't occlude the collage."""
    size = int(min(W, H) * 0.045)
    if margin_v is None:
        margin_v = int(H * 0.06)
    fnt = _font(FONT_BOLD, size)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d0 = ImageDraw.Draw(img)
    lines = _wrap(d0, text, fnt, int(W * 0.8))
    lh = int(size * 1.3)
    y0 = H - margin_v - lh * len(lines)
    pos = [((W - d0.textlength(ln, font=fnt)) / 2, y0 + i * lh, ln) for i, ln in enumerate(lines)]
    ow = max(3, round(size * 0.13))                       # ink edge
    # soft shadow halo — keeps text legible over bright art, minimal darkening
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    sd = ImageDraw.Draw(sh)
    for x, y, t in pos:
        sd.text((x + 3, y + 4), t, font=fnt, fill=(8, 6, 3, 190),
                stroke_width=ow, stroke_fill=(8, 6, 3, 190))
    img = Image.alpha_composite(img, sh.filter(ImageFilter.GaussianBlur(5)))
    d = ImageDraw.Draw(img)
    if accent:                                            # per-beat colored keyline
        a = tuple(accent[:3]) + (255,)
        kw = max(4, round(size * 0.14))
        for x, y, t in pos:
            d.text((x, y), t, font=fnt, fill=a, stroke_width=ow + kw, stroke_fill=a)
    for x, y, t in pos:                                   # cream cut-out letters + ink edge
        d.text((x, y), t, font=fnt, fill=(252, 246, 232, 255),
               stroke_width=ow, stroke_fill=(32, 22, 18, 255))
    img.save(out_path)
    return out_path


def render_title(text, out_path, W=1080, H=1920, sub=None):
    """Big centered title (dark on transparent) for the ending assembly card."""
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    size = int(min(W, H) * 0.075)
    fnt = _font(FONT_BOLD, size)
    lines = _wrap(d, text, fnt, int(W * 0.86))
    lh = int(size * 1.2)
    y = int(H * 0.1)
    for ln in lines:
        w = d.textlength(ln, font=fnt)
        d.text(((W - w) / 2, y), ln, font=fnt, fill=(40, 30, 24, 255),
               stroke_width=2, stroke_fill=(255, 255, 255, 180))
        y += lh
    if sub:
        sf = _font(FONT_REG, int(size * 0.4))
        sw = d.textlength(sub, font=sf)
        d.text(((W - sw) / 2, y + 6), sub, font=sf, fill=(150, 40, 30, 255))
    img.save(out_path)
    return out_path


def render_watermark(text, out_path, W=1920, H=1080):
    # same cut-out treatment as captions (no black box): cream text + ink edge
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    size = int(min(W, H) * 0.022)
    fnt = _font(FONT_REG, size)
    tw = d.textlength(text, font=fnt)
    x, y = W - tw - 30, H - size - 30
    ow = max(2, round(size * 0.14))
    d.text((x, y), text, font=fnt, fill=(250, 244, 232, 225),
           stroke_width=ow, stroke_fill=(18, 12, 8, 205))
    img.save(out_path)
    return out_path
