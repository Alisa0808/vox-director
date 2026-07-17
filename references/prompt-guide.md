# Prompt Guide — the heart of the Vox collage look

Two prompts decide whether the film reads as a real Vox collage or a moving poster: the
**image prompt** (makes the collage look) and the **video/motion prompt** (makes it move like
collage). Get these right and the rest is plumbing.

This one file is the whole **LOOK layer** — the prompt *structures*, the *vocabulary* that
fills them, and the ready-made *theme presets*. (The **STORY layer** — narrative arcs, pacing,
shot patterns — is its counterpart `beat-layer.md`.)

Everything below sits on top of the **common Vox constraints** (never drop these):
> torn/scissor-cut paper edges · tape · halftone dots · newspaper clippings · paper-stencil
> shapes · real paper drop-shadows · bold flat color · PRINTED/illustrated cut-outs · **NOT
> 3D, NOT CGI, NOT photoreal** · keep print grain · headline text baked in **"quotes"**.

- [1. Image prompt — structure + vocabulary](#1-image-prompt)
- [2. Video / motion prompt — structure + vocabulary](#2-video-prompt)
- [3. Why layering the image is what unlocks good AI motion](#3-layering)
- [4. Real people](#4-real-people)
- [5. Theme presets — combine the dimensions](#5-themes)

---

## 1. Image prompt

The collage look is *born here*. On the standard (whole-poster-animation) path this single
image carries the entire aesthetic, so invest in it. Structure every image prompt in 5 parts:

```
[1 STYLE BLOCK — identical on every beat]
  Mixed-media hand-cut PAPER COLLAGE, editorial zine style. Torn/scissor-cut paper edges,
  tape corners, halftone print dots, newspaper clippings, paper-stencil shapes, real paper
  drop shadows. Figures are PRINTED-texture cut-outs of real imagery (photo / woodblock /
  mural), NOT CGI, NOT a 3D render — keep print grain and paper imperfections. High-contrast.

[2 SCENE — describe as SEPARATE cut-out pieces]
  SCENE as layered paper cut-outs: {main subject}, {a prop}, {a text strip}, {a decorative
  scrap}; elements have clear edges, distinct layers, each with its own drop shadow.

[3 BACKGROUND — one bold flat color]
  on a bold flat {bg color} paper background.

[4 HEADLINE — baked in, short + bold]
  A torn-paper banner with a big bold headline "{TITLE}" (+ small subtitle), plus a red seal.

[5 TECH]
  aspect ratio {16:9|9:16|3:4}, 2k resolution.
```

### Techniques
- **Reuse the style block verbatim on every beat.** Only the scene, bg color and headline
  change. This is what makes 6 different beats feel like one film.
- **Describe distinct pieces with visible edges + shadows.** Two reasons: it looks assembled
  (collage, not a smooth painting), and it gives the *video* model separable layers to
  parallax (see §3). A blended scene can only be panned as one flat plane.
- **Bake the headline text into the image** — image models render crisp text; video models
  smear it. Keep it short, bold, 2–3 words.
- **Bold flat background color, one per beat.** Busy backgrounds muddy the cut-out silhouettes
  and kill the Vox punch. Let the palette travel across beats to carry mood (see the color
  axis below): e.g. aged sepia → bold pop colors → champion gold.
- **Say "NOT 3D / NOT CGI, printed texture, keep grain"** or the model drifts toward smooth
  render-CGI and loses the paper feel.
- **2k** so cut-outs stay crisp if scaled/animated.
- Keep a **consistent paper-texture language** across beats (edge roughness, halftone
  density); color can change, texture shouldn't.

### Worked example (2008 "KING OF EUROPE" beat, deep-red)
> Mixed-media hand-cut PAPER COLLAGE, editorial zine style; torn edges, tape, halftone dots,
> newspaper clippings, paper-stencil texture, real drop shadows; PRINTED-texture cut-outs, NOT
> 3D/CGI, keep print grain. SCENE as layered paper cut-outs: a roaring footballer in a red
> kit, a gold trophy, a big cut-out "7", a torn "KING OF EUROPE" newspaper strip, a club
> crest, scattered geometric scraps — clear edges and drop shadows. Bold flat deep-red paper
> background. Torn-paper banner headline "KING OF EUROPE" + small subtitle, red seal. 3:4, 2k.

### The image dimensions (pick one term per axis to fill the structure)
The style block above is the default. To differentiate a topic — or compose a custom theme —
choose a term from each axis. (⭐ = the strongest theme levers.)

| Dimension | Controls | Vocab bank (mix & match) |
|---|---|---|
| **Medium/technique** | the strongest style lever | paper collage · torn-paper collage · photomontage · screenprint · **risograph** · letterpress · linocut/woodcut · lithograph · halftone print · gouache · flat vector · photocopy/xerox · rubber-stamp |
| **Art movement / era** ⭐ | single best "theme knob" — shifts palette+type+layout at once | Swiss/International Typographic · Bauhaus · mid-century modern · Russian Constructivism · Dada photomontage · Pop Art · psychedelic '60s · punk zine · Memphis · Art Deco · WPA/vintage travel poster · Soviet · atomic-age · retro-futurism |
| **Composition/layout** ⭐ | poster hierarchy + negative space | modular grid · asymmetric · strong negative space · diagonal dynamic · foreground–midground–background depth · hero headline + subhead hierarchy · full-bleed · radial · stacked bands · off-center focal |
| **Color palette** ⭐ | cleanest theme distinguisher (stops muddy gradients) | limited 2–3 color · duotone · monochrome + 1 accent · **riso fluorescent-pink + federal-blue** · Bauhaus primaries (red/yellow/blue) · '70s mustard/rust/avocado · '60s pop (hot-pink/orange) · teal-&-orange · CMYK process · cream/kraft base · neon-on-black · named hex (e.g. `#0047AB`) |
| **Typography treatment** ⭐ | headline LOOK (we only passed the words) | **put exact words in "quotes"** + name a REAL type style: bold condensed grotesque (Helvetica/Akzidenz) · geometric sans (Futura/Bauhaus) · slab serif · '70s display serif · wood-type · hand-lettered · **ransom-note cut-out letters** · stencil · all-caps · knockout/reversed · huge headline + small caption |
| **Print finish / texture** | "made by hand, not AI-slick" | halftone dots · **Ben-Day dots** · riso ink misregistration/overprint · letterpress deboss · newsprint · kraft/cardstock · aged/foxed paper · fold creases · coffee stains · deckled vs scissor-cut edges |
| **Lighting / capture** | keeps it "scanned" not "rendered" (anti-3D) | flat even studio light · shadowless scanned-document light · straight-on/head-on · flat-lay top-down · subtle paper drop-shadows |
| **Mood** | tone anchor | playful · bold · urgent · editorial/serious · nostalgic · optimistic · ominous · satirical · activist/protest |

**One-line image structure** (consensus of Nano-Banana/Ideogram/OpenAI/Flux — Ideogram is
"format-first", best for baked text):
`[MEDIUM] + [ART MOVEMENT/ERA] of [SUBJECT + SCENE], [COMPOSITION/hierarchy/negative space],
[straight-on scanned-flat framing] + [flat even light, paper drop-shadows], [named limited COLOR
PALETTE], [PRINT FINISH/texture], headline "EXACT WORDS" in [NAMED TYPE STYLE] [placement], [MOOD],
[aspect]` — then per model: Omni/Nano-Banana/Flux/DALL·E take **no negatives** (phrase positively);
SDXL needs a negative field; Midjourney uses `--no` + params last.
Sources: Nano-Banana https://deepmind.google/models/gemini-image/prompt-guide/ · Ideogram
https://docs.ideogram.ai/using-ideogram/prompting-guide/2-prompting-fundamentals · OpenAI
https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide · Flux
https://docs.bfl.ml/guides/prompting_summary · Midjourney https://docs.midjourney.com/hc/en-us/articles/32859204029709-Parameter-List

---

## 2. Video prompt

The motion prompt turns "pan a poster" into "a living collage". Use the **5-axis** structure
(this is the structure from the reference cr7 Omni prompt — all five axes matter, especially
**feel** and **color**, which set mood and palette movement):

```
[GOAL] Animate this still into a mixed-media collage MOTION GRAPHIC. Keep it flat 2D paper,
       NOT 3D, no photoreal.

[AXIS 1 · CAMERA]   one smooth continuous move for this shot: {slow push-in | lateral
                    parallax pan | slow rise}.
[AXIS 2 · MOVEMENT] layered paper cut-outs drift with visible drop-shadow parallax; elements
                    and geometric scraps bob/settle gently on the beat; halftone dots pulse;
                    torn edges and tape flutter; a breathing quality.
[AXIS 3 · AESTHETIC]preserve the torn-paper / tape / halftone / newspaper / paper-stencil
                    textures exactly; keep the bold flat background.
[AXIS 4 · FEEL]     {emotional tone of this beat} — e.g. tender / triumphant / cinematic
                    editorial, "a page from a scrapbook".
[AXIS 5 · COLOR]    {this beat's palette}, high contrast; if part of an arc, name where it
                    sits (aged sepia → bold pop → champion gold).

[CONSTRAINTS] keep the layout, the seal and ALL on-screen text perfectly stable and legible;
              ONE smooth continuous move — absolutely NO sudden zoom snaps, NO jump-cuts, NO
              teleporting/re-framing inside the shot; no new objects, no morphing, no drift.
```

### Techniques
- **The MOVEMENT axis is the lever** that makes Omni move *layers* (parallax) instead of
  sliding the whole frame. Name the layered paper motion explicitly.
- **FEEL and COLOR are not decoration** — they steer the model's pacing and grade. A "tender,
  sepia" beat animates slower and warmer than a "triumphant, gold" beat. Don't drop them.
- **The CONSTRAINTS axis prevents the common breaks**: text wobble, 3D drift, and the big one
  — internal jump-cuts.
- **Never write "snap / punch-in / slam / quick zoom".** Omni over-reacts and generates a
  jump *inside* the shot that reads as a one-frame flash. Ask for ONE smooth continuous move.
- **Don't rely on the video model for text** — it's already baked in the keyframe; just tell
  the model to keep it stable.
- **One move per shot.** For richer editing, cut between multiple short shots (wide + detail)
  rather than asking one clip to do a complex timeline.

### The full axis vocabulary (the 5 axes above, expanded with the STABILITY axes)
The core 5 axes set mood and motion; the extra axes below (⭐⭐) are what actually control
STABILITY — they fix the loop / text-wobble / morph failures. Pick phrasing per axis.

| Axis | Controls | Vocab / phrasing |
|---|---|---|
| **Motion amplitude** ⭐⭐ | THE anti-morph/anti-text-warp lever | `very subtle` · `minimal` · `moderate` · "~5% movement" · avoid `intense/large/explosive` near text |
| **Camera move** | how the camera travels | **safe for flat paper:** static/locked-off · slow push-in/pull-out · slow pan/tilt · subtle parallax truck. **Bold (bend 2D toward fake 3D, use with `constraints: loose` + re-roll):** orbit · crane · dolly-zoom · roll · 3D arc |
| **Shot size / angle** | framing | full poster in frame (default) · slow push to a detail · **eye-level straight-on (default)** · overhead (reads as paper on a table) |
| **Element motion** | what moves inside | **safe paper-native verbs:** drift · sway · ripple · flutter · slide · pivot (rigid) · bob · pulse · shimmer · settle · parallax between layers. **Bold (loose + re-roll):** warp · transform · morph · vortex · explode |
| **Speed / easing** | tempo | slow · gentle · continuous · ease-in-ease-out · (risky: quick/snap/whip) |
| **Lighting-over-time** | best "safe motion" for flat art | soft light sweep across the surface · gentle shadow drift · subtle flicker/glow pulse |
| **Dimensional lock** ⭐ | keep it flat | "flat 2D, camera parallel to the poster, no 3D rotation, no perspective change; paper layers parallax only, elements slide/pivot as rigid flat paper, do not bend or morph" |
| **Stability anchors** ⭐⭐ | protect text/layout | "the printed headline, logo and layout stay sharp, legible and perfectly stable — do not redraw, distort or move the lettering" |
| **Shot structure** | cuts / loop | "single continuous shot, no cuts, no scene changes" · one-way: add a **motion endpoint** ("…then settles into place") · seamless loop: say "looping video" (Luma) |

### Best-practice rules that fix our bugs (all from official guides)
1. **Describe motion, not the picture.** The still already has subject/scene/text/style —
   restating them (esp. the text) makes the model re-synthesize and warp them. (Runway, Veo, Kling.)
2. **One camera move + one action per shot.** Multiple simultaneous moves = instability/morph.
   (Sora, Seedance: "specify only 1 type of camera movement… increases image instability".)
3. **Keep amplitude small; motion physically plausible.** (Kling, Seedance: "slow, gentle,
   coherent subtle movements… avoid high-burst, large-dynamic actions".)
4. **Positive phrasing only for Omni/Veo/Runway** — "no/don't" backfires ("may result in the
   opposite"). **Kling & Seedance DO support negative prompts.** Know your model.
5. **Text:** don't ask the video model to render text; anchor it as stable; keep motion away
   from the text region; **for critical text, overlay in post.** (Cross-source.)
6. **Anti-loop:** give a one-way move a settle endpoint, or say "single continuous"; short
   clips shouldn't over-script per-second beats. (Kling, Runway Gen-4.)
7. **Flat-collage:** name the style ("flat 2D paper cutout animation, rigid paper layers")
   and lock dimensionality → steers the model away from 3D morphing. (Storyblocks + rules above.)

**One-line video structure** (I2V, adapted): `[SHOT SIZE+ANGLE] + [CAMERA MOVE + AMPLITUDE] +
[ELEMENT MOTION + SPEED/EASING] + [LIGHTING-OVER-TIME] + [AESTHETIC/TEXTURE + DIMENSIONAL LOCK] +
[FEEL] + [COLOR] + [STABILITY ANCHORS] + [SHOT STRUCTURE/LOOP]`.
Sources: Runway https://help.runwayml.com/hc/en-us/articles/39789879462419 · Kling I2V
https://kling.ai/quickstart/image-to-video-guide · Seedance https://docs.byteplus.com/en/docs/ModelArk/2222480 ·
Veo https://cloud.google.com/blog/products/ai-machine-learning/ultimate-prompting-guide-for-veo-3-1 ·
Sora https://developers.openai.com/cookbook/examples/sora/sora2_prompting_guide · StudioBinder camera
glossary https://www.studiobinder.com/blog/different-types-of-camera-movements-in-film/

---

## 3. Layering

Common question: *"can I feed a background + separate component images to the video model to
get dramatic component motion?"* In practice, no — Omni/Kling `reference-to-video` is
**generative**, not a layer compositor: it reinterprets the refs and invents its own motion,
so you get *less* control, not more. For controlled per-element choreography, use the local
engine (`references/local-engine.md`).

But there's a real lever within the standard path: **the more clearly layered your keyframe
is, the more layered motion the video model can produce.** Distinct cut-outs with edges and
shadows → the model can drift them at different depths (parallax) → "living collage". A flat,
blended image → only a whole-frame pan is possible. So push the *layering* in the image
prompt (§1) if you want livelier auto-motion.

---

## 4. Real people

Real-person keyframes are fine to *generate* (use web-search grounding or a reference photo
with an edit model to anchor the face). The catch is *animation*: Google (Omni) and ByteDance
(Seedance) refuse recognizable celebrities / brand logos ("prohibited contents" /
"digital-rights"). Two ways through:
- **Kling O3 pro** allows real people — set it as `video_model` (simplest).
- **Local engine** — animating cut-outs frame-by-frame never touches a video model's content
  filter, and gives full control. Best when you also want dramatic element choreography.

---

## 4b. C-roll anchor locks (photo → poster, validated 2026-07-17)

C-roll's whole trick is one photographic sticker that never gets redrawn while the paper
world is generated around it. Three lock templates, each earned by a failed generation
(`croll_keyframes.py` bakes them in — reproduced here for hand-run prompts):

**FACE LOCK (portrait).** "Her/his face and hair from the attached photo are cut out as a
PHOTOGRAPHIC sticker with a torn white paper border — keep the facial identity, features and
the exact expression from the photo pixel-faithful; do not redraw, repaint or stylize the
face; NO halftone dots, print texture or ink treatment on the face or hair. All poses and
gestures are expressed by the body only. From the neck down the body is a hand-drawn
paper-doll illustration jointed like a vintage paper puppet, FULLY CLOTHED in {outfit}."
- *Poses go to the body only*: asking the model for a wink or a smile redraws the face.
- *Scope halftone to the background* or the print dots bleed onto skin.
- *Lock the clothing* or the paper-doll body drifts (one run produced a bare mannequin).

**PRODUCT LOCK.** "{The product} from the attached photo is cut out as a PHOTOGRAPHIC
sticker with a clean scissor-cut edge and a soft real paper drop shadow — keep its exact
shape, materials, surface reflections and every word of its label typography pixel-faithful.
Do not redraw, restyle or repaint the subject or its label. Re-style ONLY the world around
it as printed paper collage."

**ANCHOR FREEZE (the video stage).** Image-edit keeps label typography intact, but the
image-to-video stage can quietly re-letter it (observed: "PARFUM" → "PAREUM") or re-time a
face. Every C-roll motion prompt therefore carries a freeze line — "the photographic
sticker (and every letter of its label) is a frozen layer, pixel-identical to the still for
the entire duration" — written into beats.json as `anchor_freeze` and injected by
`clips.py`. Extract a frame per clip and re-check the letters anyway.

Note the permission split (same spirit as A-roll's face rule): edit models will *carry* a
real face/product verbatim but Omni refuses to *repaint* one — a halftone-textured face was
rejected at the video stage regardless of phrasing, and Kling accepts it but drifts the
identity. Photographic-sticker treatment is the reliable lane.

---

## 5. Theme presets — combine the dimensions

A **theme preset** = one pick from each image dimension (§1) + a motion preset (§2), on top of
the common Vox constraints. This is how we offer "different theme options" without
hand-writing each prompt. The library (`styles.THEME_PRESETS`):

| Preset | Era/movement | Palette | Type style | Print finish | Motion preset | Fits topics |
|---|---|---|---|---|---|---|
| `american-retro` | 1950s US ad/pulp | bold retro primaries | wood-type / bold slab | halftone, aged | punchy | ads, sports, business, money |
| `swiss-modern` | Swiss/Intl Typographic | 2-color + red accent | Helvetica/Akzidenz grotesk | clean flat, subtle grain | calm | tech, finance, explainers |
| `punk-zine` | 90s punk/DIY | B&W + 1 spot color | ransom-note cut letters | photocopy, misregistration | punchy/max | rebellion, music, counterculture |
| `soviet-constructivist` | Russian Constructivism | red/black/cream | bold condensed diagonal | letterpress, newsprint | punchy | politics, revolution, industry |
| `wpa-propaganda` | 1930s WPA poster | muted 3-color | stencil / gothic | screenprint grain | calm | history, labor, public health |
| `70s-groovy` | 1970s | mustard/rust/avocado | bulbous display serif | riso grain | punchy | culture, food, nostalgia |
| `chinese-ink` | Chinese woodblock/ink | ink + vermilion | Chinese brush + red seal | rice-paper, seal | calm/punchy | Chinese history/culture |
| `atomic-age` | 1950s futurism | teal/orange/cream | atomic script | halftone | punchy | science, space, future |
| `newsprint-editorial` | mid-century front-page news feature | cream/deep red/mustard/charcoal | bold condensed newsprint headline | aged paper, heavy halftone | punchy | news, AI/tech explainers, editorial features |
| `gilded-deco` | 1920s art-deco luxury advertisement | aged cream/champagne gold/charcoal | elegant didone serif, wide tracking | gold foil, fine halftone | calm | luxury goods, perfume, watches, heritage brands |

**How to use:** the agent reads the topic → suggests 3–4 fitting presets (or composes a new one
by mixing the banks in §1–§2) → `style_bakeoff.py` renders one beat in each → the user picks. The
picked preset's fields drop into the image prompt (via `collage_style` + palette/type/finish) and
its `motion_style` into the video prompt. The common Vox constraints and stability anchors are
always on.
