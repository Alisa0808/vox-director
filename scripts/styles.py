#!/usr/bin/env python3
"""
Per-era style bible for vox-director (validated on Atlas Cloud / Nano Banana 2).

Each STYLE_BASE is scene-agnostic: it fixes ONLY the visual idiom of a dynasty.
compose_keyframe_prompt() appends the beat's scene + a shared bilingual
title/seal treatment so the whole film stays coherent while the style evolves.
"""

# The "evolution" arc: the visual idiom evolves with the civilization.
STYLE_BASES = {
    "tang": (
        "Classical Chinese gongbi fine-line court painting fused with Dunhuang mural "
        "style, painted with mineral pigments (ochre, vermilion, malachite green, lapis "
        "blue, gold) on aged cracked silk with flaking patina, elegant flowing brushwork "
        "and decorative cloud motifs. Ornate, luminous, museum handscroll aesthetic."
    ),
    "song": (
        "Song Dynasty literati ink-wash painting in the minimalist 'one-corner' "
        "manner of Ma Yuan and Xia Gui: vast empty negative space, sparse delicate "
        "monochrome ink with the faintest grey wash on aged cream silk, misty and "
        "restrained. Quiet, refined, elegant."
    ),
    "ming": (
        "Blue-and-white porcelain illustration: cobalt-blue underglaze brushwork "
        "on a white porcelain ground with subtle celadon crackle-glaze texture, flowing "
        "porcelain-painting line and wash, decorative wave and cloud borders. Elegant, "
        "iconic, ceramic aesthetic with aged patina."
    ),
    "qing": (
        "Aged late-imperial Chinese court painting on dark silk in the fusion "
        "Sino-European manner of Giuseppe Castiglione, in a somber twilight palette of "
        "deep crimson, fading imperial gold and dusk shadows. Fine detailed brushwork, "
        "darkened silk with patina. Melancholic, ornate, empire-in-decline mood."
    ),
    "modern": (
        "High-contrast black-and-white woodcut print in the 1930s Chinese modern woodcut "
        "movement style (Lu Xun era), with the grain of an aged sepia photograph. Bold "
        "gouged black-and-white lines, rough carved texture, torn newsprint edges, "
        "sepia-and-ink tone. Stark, urgent, revolutionary."
    ),
    "rising": (
        "Bold contemporary minimalist 'new Chinese' graphic poster: elegant "
        "modern flat shapes with fine gold linework and a touch of ink-brush energy, a "
        "palette of bold red, deep ink and gold, generous negative space, dynamic upward "
        "motion. Sleek, powerful, optimistic, classical-modern fusion."
    ),
}

# Shared treatment so the evolving styles still read as one film.
TITLE_TREATMENT = (
    "Include a title cartouche with large red Chinese characters '{title_cn}' and a "
    "small clean English subtitle '{title_en}', plus a single red seal stamp. Keep the "
    "headline crisp and legible."
)

# ---- Paper-collage STYLE LIBRARY (pick per topic; hybrid selection) --------------
# Shared collage MECHANICS (same for every style) — only the visual IDIOM changes.
# The library is a palette + quality floor, NOT a fixed menu: Claude reads the topic,
# picks the 3-4 idioms that fit its era/culture/tone (or composes a custom one), runs a
# bake-off, and the human picks. Match the idiom to the TOPIC, not the language — an English
# film about Chinese history should still look Chinese (that's fine). The goal is the right
# look per topic, not a fixed default culture.
COLLAGE_MECHANICS = (
    "Clearly layered hand-cut paper cut-outs with visible torn and scissor-cut edges, tape "
    "corners and soft real paper drop shadows, on a bold flat {bg} paper background. Halftone "
    "print dots, newspaper-clipping scraps, paper-stencil shapes, aged paper texture, slight "
    "print misregistration, scattered geometric paper accents (triangles, circles, zigzags, "
    "washi tape). Figures are PRINTED / illustrated cut-outs, NOT CGI, NOT a 3D render — keep "
    "print grain and paper imperfections. High-contrast, punchy, tactile, hand-assembled."
)

STYLE_LIBRARY = {
    "american-retro": (
        "Vintage 1950s-60s American advertising and pulp-magazine paper collage: bold flat "
        "retro colors, mid-century engraved and illustrated Western cut-out figures, classic "
        "Americana printed imagery, nostalgic."
    ),
    "modern-flat": (
        "Clean modern flat 2D illustrated collage in the Vox explainer motion-graphic style: "
        "bold flat-color vector-illustration cut-outs, simple confident shapes, a limited "
        "contemporary palette, crisp infographic editorial layout."
    ),
    "zine": (
        "Gritty punk zine / ransom-note collage: torn newspaper and magazine scraps, cut-out "
        "mismatched headline letters, photocopied high-contrast halftone, black-and-white with "
        "one spot color, raw hand-cut edges. DIY, analog, urgent."
    ),
    "photo-collage": (
        "Cinematic documentary photo-collage: real black-and-white archival photographs cut "
        "out and layered with soft drop shadows, one restrained accent color, sepia and "
        "monochrome vintage photography. Serious, editorial, museum-like."
    ),
    "chinese-ink": (
        "Mixed-media collage of Chinese woodblock-print and ink-mural cut-out figures, aged "
        "rice-paper and Chinese newspaper clippings, vermilion seal stamps. Oriental, historical."
    ),
}
DEFAULT_STYLE = "american-retro"

# THEME PRESETS = full "look" bundles (theme-layer). A preset fixes the LOOK dims (idiom +
# palette + type + finish + mood + default motion energy); scene/camera/element-motion stay
# per-beat (beat-layer); Vox constraints + text/flat locks are universal. Extensible: Claude may
# compose a custom theme by mixing prompt-guide.md dimensions when a topic needs one the library lacks.
THEME_PRESETS = {
    "american-retro": {"idiom": "american-retro", "palette": "bold retro primaries — red, mustard, teal, cream",
        "type_style": "bold wood-type / heavy slab, all-caps", "finish": "heavy halftone dots, aged newsprint, slight misregistration",
        "mood": "nostalgic, punchy", "motion_style": "punchy"},
    "swiss-modern": {"idiom": "modern-flat", "palette": "two-color + one red accent, lots of white",
        "type_style": "Helvetica/Akzidenz grotesque, tight caps", "finish": "clean flat, very subtle grain",
        "mood": "precise, confident", "motion_style": "calm"},
    "punk-zine": {"idiom": "zine", "palette": "black & white + one fluorescent spot color",
        "type_style": "ransom-note cut-out mismatched letters", "finish": "photocopy grain, heavy misregistration",
        "mood": "urgent, rebellious", "motion_style": "max"},
    "soviet-constructivist": {"idiom": "Russian Constructivist photomontage, bold diagonal geometry",
        "palette": "red, black, cream", "type_style": "bold condensed gothic set on strong diagonals",
        "finish": "letterpress, newsprint", "mood": "heroic, urgent", "motion_style": "punchy"},
    "wpa-propaganda": {"idiom": "1930s WPA / vintage travel silkscreen poster",
        "palette": "muted 3-color screenprint", "type_style": "gothic / stencil caps",
        "finish": "screenprint grain, flat ink", "mood": "earnest, civic", "motion_style": "calm"},
    "70s-groovy": {"idiom": "1970s groovy print", "palette": "mustard, rust, avocado, cream",
        "type_style": "bulbous 70s display serif", "finish": "riso grain, warm", "mood": "warm, funky", "motion_style": "punchy"},
    "chinese-ink": {"idiom": "chinese-ink", "palette": "ink black + vermilion, aged paper",
        "type_style": "Chinese brush characters + small English + red seal", "finish": "rice-paper, ink bleed",
        "mood": "elegant, historical", "motion_style": "calm"},
    "atomic-age": {"idiom": "1950s atomic-age retro-futurism", "palette": "teal, orange, cream",
        "type_style": "atomic script + geometric caps", "finish": "halftone, starbursts",
        "mood": "optimistic, bright", "motion_style": "punchy"},
}


def resolve_theme(name):
    """Theme name -> full look bundle (or None). Use to drive keyframes + motion_style."""
    return THEME_PRESETS.get(name)


def _headline(title_cn, title_en, style, type_style=None):
    if title_cn:                                   # bilingual (CJK styles)
        return (" " + TITLE_TREATMENT.format(title_cn=title_cn, title_en=title_en))
    ts = f" in {type_style}" if type_style else ""
    seal = "a vermilion seal stamp" if style == "chinese-ink" else "a small paper sticker accent"
    return (f" Include a torn-paper banner with a big bold cut-out English headline "
            f"'{title_en}'{ts} and {seal}. Keep the headline crisp and legible.")


def compose_collage_prompt(scene, title_cn, title_en, bg="warm ochre", aspect="16:9",
                           with_title=True, style=DEFAULT_STYLE,
                           palette=None, type_style=None, finish=None):
    """Paper-collage keyframe prompt. `style` = a STYLE_LIBRARY idiom name (or custom string).
    palette/type_style/finish come from the chosen THEME_PRESET (theme-layer) and sharpen the
    look. Culture/topic-matched. with_title=False for detail cut-in shots."""
    idiom = STYLE_LIBRARY.get(style, style)        # named -> library; else treat as custom
    pal = f" Palette: {palette}." if palette else ""
    fin = f" Print finish: {finish}." if finish else ""
    block = f"{idiom}{pal} {COLLAGE_MECHANICS.format(bg=bg)}{fin}"
    if with_title:
        title = _headline(title_cn, title_en, style, type_style)
    else:
        title = " No big headline in this shot (a small accent only); it is a cut-in detail."
    return (f"{block} SCENE (as layered paper cut-outs): {scene}.{title} "
            f"Aspect ratio {aspect}.")


def compose_keyframe_prompt(era: str, scene: str, title_cn: str, title_en: str,
                            aspect: str = "16:9") -> str:
    base = STYLE_BASES[era]
    title = TITLE_TREATMENT.format(title_cn=title_cn, title_en=title_en)
    return (
        f"{base} SCENE: {scene}. Arrange the composition with one clear focal subject "
        f"and strong editorial poster balance. {title} Aspect ratio {aspect}."
    )
