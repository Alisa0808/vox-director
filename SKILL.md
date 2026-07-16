---
name: vox-director
description: >
  Turn ONE topic into a finished Vox-style paper-collage explainer / ad video, end to end
  on the Atlas Cloud API + local ffmpeg — script, collage keyframes, motion, voice-over,
  music, captions, all automated. Use this whenever the user wants a "Vox style" video,
  a paper/torn-paper collage animation, a "motion collage", a narrated explainer or short
  ad built from AI-generated collage posters, a scrapbook-style tribute, or wants to turn
  a topic / product / person into a punchy narrated collage video — even if they don't say
  the word "Vox". Also use when reproducing Stav Zilber / rom1trs / Higgsfield-style collage
  ad workflows, or when the user asks for a motion collage or a scrapbook-style tribute.
  Triggers: "vox video", "collage video", "motion collage", "paper collage
  explainer", "make a collage ad", "turn this topic into a collage video".
---

# Vox Director

Turn a one-line topic into a finished **Vox-style paper-collage video**: a bold, punchy,
narrated explainer/ad where each beat is a torn-paper collage poster that comes alive, with
voice-over, music and captions. Runs on **one Atlas Cloud API key** + local **ffmpeg**.

The look is the modern editorial paper-collage popularized by Vox explainers and creators
like Stav Zilber / rom1trs: hand-cut paper cut-outs, torn edges, tape, halftone dots,
newspaper clippings, bold flat color per beat, big cut-out headlines.

## The core idea (read this first)

The Vox collage look and the collage motion are **two different steps**:

1. **The look is born in the IMAGE step.** Each beat is a finished collage *poster* made by a
   text-to-image model. All the collage DNA (torn paper, cut-outs, halftone, bold color,
   headline text) lives in that image. If the image isn't a rich collage, nothing downstream
   will save it.
2. **The motion is added after.** By default an AI video model animates the whole poster (the
   "living poster" path — simple, automated). For dramatic *piece-by-piece* assembly you cut
   the poster into parts and drive them with the local keyframe engine (advanced path).

Everything hinges on the prompts. **Before writing any image or video prompt, read
`references/prompt-guide.md`** — it has the exact prompt structures that make the difference
between "a real Vox collage" and "a moving PowerPoint".

## Prerequisites (check, don't skip)

- `echo "${ATLASCLOUD_API_KEY:+set}"` — if empty, tell the user to set it (get one at
  https://www.atlascloud.ai/console/api-keys) and stop.
- `command -v ffmpeg ffprobe` — required for assembly (`brew install ffmpeg` on macOS).
- `python3 -c "import PIL"` — Pillow, for captions/watermark overlays.

## Standard workflow (topic → film)

This is the default, most-automated path. Every stage is one script, all driven by a single
`beats.json` per project under `out/<project>/`.

1. **Topic → beat map.** First **read `references/beat-layer.md`** (the story layer) and pick a
   narrative `arc` that fits the topic (`timeline` for history, `pas`/`bab` for ads,
   `how_it_works` for explainers, `man_in_hole` for transformations, …). Then write
   `out/<project>/beats.json` following that arc: **beat-1 headline must be a ≤3s hook**; beat
   count per duration (30s→6–8, 60s→10–12); split each beat into **2 shots** (wide+detail) with
   **per-shot `camera_move` VARIED across adjacent beats** (never repeat; `static` on the payoff)
   and **rich `element_motion`** (see step 4). Each beat: `narration`, `title_cn`/`title_en`,
   `scene`, `bg`, `feel`, `hook`. This draft is the **first mandatory approval gate** — show the
   user the beat map before generating (the aspect-routing approximation in step 4 is the other
   one). Examples in `examples/`.

2. **Pick the visual style (hybrid — do this BEFORE keyframes).** Do not reuse one house style
   for every topic. Read `references/prompt-guide.md` (§5 theme presets); pick 3–4 **theme presets**
   (`styles.THEME_PRESETS`: `american-retro`, `swiss-modern`, `punk-zine`,
   `soviet-constructivist`, `wpa-propaganda`, `70s-groovy`, `chinese-ink`, `atomic-age`,
   `newsprint-editorial`) that fit
   the topic's era/culture/tone — **or compose a custom theme** by mixing the prompt-guide dimensions
   (medium/era/palette/type/finish) when none fit. Match the topic, **not** the language (an
   English film on Chinese history should look Chinese). A theme bundles the whole LOOK layer
   (idiom+palette+type+finish+mood+motion). Run a bake-off and let the user pick by eye — AI
   proposes, the library is the quality floor, the human decides. Set the pick as `"theme"`:
   `python3 scripts/style_bakeoff.py out/<project> american-retro,swiss-modern,punk-zine,atomic-age`
   Set the chosen name as `"collage_style"` in beats.json (keyframes.py reads it).

3. **Keyframes (the collage look).** `python3 scripts/keyframes.py out/<project>`
   Generates one collage poster per beat/shot with **google/nano-banana-2/text-to-image**,
   headline text baked in. Compose prompts with the 5-part structure in
   `references/prompt-guide.md`. Verify each poster looks like a *real layered collage*
   before animating — re-roll cheap ($0.08) here rather than paying to animate a weak image.

4. **Motion.** `python3 scripts/clips.py out/<project>`
   Animates each poster with **google/gemini-omni-flash/image-to-video**. Two independent axes
   (see `references/beat-layer.md` §3, tested on our stack):
   • **`camera_move`** — ONE move per shot. Safe/default: `{static, push_in, pull_out, pan, tilt,
     parallax}`. **Bold/experimental** `{orbit, dolly_zoom, roll, whip}` are **available, not
     banned** — they can warp the flat art, so pair with `constraints: loose` and **re-roll**.
     Any custom phrase also passes through.
   • **`element_motion`** — where the energy lives; **AI writes it per beat to fit that scene** (not a
     template). Make it RICH (several elements moving) — be bold. A **hero element flying across
     the frame** (paper bird/plane/coins) is a great **occasional** punch on a key beat, **not
     every shot** (a flyer in every frame reads as a formula).
   `motion_style` = amplitude `calm | punchy | max` (the theme sets a default). **`constraints`**
   = `strict` (default: defect guards on — flat-2D, one-way, no-morph; best for clean text-heavy
   explainers) or `loose` (let the model explore 3D/bold moves; re-roll the misses). **Headline
   text is hard-protected only on shots that have a title** (detail shots without a headline are
   free to go wild). For **real people / brand logos**, Omni & Seedance refuse — set
   `"video_model": "kwaivgi/kling-video-o3-pro/image-to-video"`.
   **Aspect routing** (`styles.resolve_video_aspect`, second approval gate): `clips.py` resolves
   `doc["aspect"]` against the chosen `video_model`'s own supported ratios — exact match wins;
   Omni is 16:9/9:16 only, Kling reference-to-video adds 1:1, Kling image-to-video/video-edit and
   Seedance just follow the input/ratio param. When there's no exact match it picks the nearest
   ratio but **stops and asks you to confirm** (set `"aspect_approx_confirmed": true` once you
   have) rather than silently reframing the film — every clip in one run shares the same resolved
   aspect so the finished film is never mixed.

5. **Voice + music.** `python3 scripts/audio.py out/<project>`
   One consistent narrator via **xai/tts-v1** + instrumental BGM via **minimax/music-2.6**.
   **Pick `voice_id` to fit the topic + language** (don't just keep the default) — see
   `references/voices.md` for the full roster (5 multilingual + ~66 native voices by language,
   with gender). Default `leo` (male, documentary). (Do NOT use seed-audio for plain narration
   unless you pin a speaker — see gotchas.)

6. **Assemble.** `python3 scripts/assemble.py out/<project>`
   ffmpeg: normalize + concat all shots, lay the single narration ducked under the music,
   burn captions timed per beat, add the watermark. Output `out/<project>/final.mp4`.

7. **Verify.** You can't read an mp4 directly — extract frames to jpg and look:
   `ffmpeg -ss <t> -i final.mp4 -vf "scale=640:-1,format=yuvj420p" -frames:v 1 f.jpg`

### Cadence — how long shots should be

A common mistake is one long shot per beat. On a 9:16 / social piece especially, a static
10s shot reads as dead air. Aim for a **cut every ~4–6 seconds**:

- **Shots run 3–6s; never let a single shot exceed ~7s** — beyond that the AI motion has
  nowhere to go and it feels static.
- **A beat's narration is ~8–10s, so give each beat 2 shots** (a *wide* establishing shot with
  the headline + a *detail* cut-in without it). The narration plays continuously across both;
  the visual cuts mid-sentence. This is the single biggest rhythm win.
- So a ~60s film is typically **~6 beats × 2 shots × ~5s = 12 shots**, not 6 × 10s.
- Reuse the wide keyframe as shot `a`; generate a tighter detail scene for shot `b`.
  `keyframes.py` skips any shot that already has a `keyframe_url`, so adding `b` shots and
  re-running only generates the new ones.

Add a `shots` array to each beat (see schema). Give each shot its own short `scene` and
`motion`; set `"title": true` only on the wide shot so the headline shows once per beat.

## A-roll mode (talking-head → collage)

The standard workflow above is **B-roll**: a topic becomes AI-generated collage posters
that get animated. **A-roll is the reverse case** — the user already has a real recorded
talking-head video (a presenter speaking to camera) and wants it *itself* turned into the
collage look, keeping their actual performance (face, lip movement, gestures) intact. There
is no poster to generate; the "keyframe" is the presenter's own footage. Use A-roll when the
user gives you a video file of themselves/a presenter talking, not a topic to write from
scratch.

1. **Transcribe + auto-segment.** `python3 scripts/asr_beats.py <project_dir> <source.mp4>`
   Runs xai/stt-v1 on the source's own audio and cuts it into beats at sentence-ending
   punctuation or natural pause gaps (never exceeding ~9.5s, under Omni/Kling video-edit's
   10s per-call cap). Writes `beats.json` with each beat's `start`/`end`/`text` — **this is
   the same mandatory approval gate as the B-roll beat map**: review it, set `"theme"` (run
   `style_bakeoff.py` the same way — the presenter's segment works fine as the bake-off
   source), and optionally fill in a `content_beats` string per beat (a sticker/stamp idea
   to layer in) before generating anything.

2. **Generate.** `python3 scripts/aroll_clips.py <project_dir> [only_ids]`
   Cuts each beat's time range out of the source, uploads it, and re-styles it with a
   **photographic paper-cutout sticker** treatment on the presenter — her real likeness,
   lip movement, eye-line and gestures follow the source frame-for-frame; only the
   silhouette edge and the world around her are paper-collage. Default model is
   `google/gemini-omni-flash/video-edit`; any beat it rejects automatically retries on
   `bytedance/seedance-2.0/reference-to-video` (set via `video_model`/`video_model_fallback`
   in beats.json). **Never ask the model to redraw or halftone-texture the face itself** —
   that gets rejected regardless of how the prompt is worded (tried both a strong and a
   softened phrasing; both failed). Uses the same aspect-routing confirm gate as `clips.py`.

3. **Assemble.** `python3 scripts/aroll_assemble.py <project_dir>`
   Muxes each generated clip with the *original* beat segment's own audio (never whatever
   audio the video model produced) so lip-sync is guaranteed regardless of which model
   handled that beat, normalizes every beat to one canvas, and concats into `final.mp4`.

## beats.json schema

```json
{
  "project": "my-film", "topic": "...", "language": "en",
  "aspect": "9:16",                       // 16:9 | 9:16 | 1:1 | 3:4
  "style": "collage",
  "provider": "atlas_cloud",              // media backend — default; pluggable (scripts/provider.py)
  "theme": "american-retro",              // THEME_PRESET (styles.THEME_PRESETS) — the LOOK layer
  "arc": "timeline",                      // narrative arc (beat-layer.md) — the STORY skeleton
  "video_model": "google/gemini-omni-flash/image-to-video",  // Kling for real people
  "image_model": "google/nano-banana-2/text-to-image",       // keyframes; or openai/gpt-image-2/text-to-image
  "image_resolution": "1k",               // 1k (default) | 2k | 4k
  "video_resolution": "720p",             // 720p (default); Seedance also 480p/1080p (Omni is 720p-only)
  "motion_style": "punchy",               // amplitude: calm | punchy | max (theme sets a default)
  "constraints": "strict",                // strict = defect guards on | loose = let AI explore + re-roll
  "voice": {"voice_id": "leo", "language": "en", "speed": 1.0},  // pick per topic/language — see references/voices.md
  "music": "epic cinematic orchestral, instrumental, no vocals",
  "mix": {"music": 0.6, "voice": 1.25},   // audio balance — optional; these are the defaults (BGM ducks under the VO)
  "caption_style": "white",               // white (default: clean white subtitle) | paper (cream cut-out collage look)
  "watermark": "Made with Atlas Cloud",
  "beats": [
    {
      "id": 1, "title_cn": "", "title_en": "BEFORE MONEY",
      "bg": "earthy clay tan", "feel": "ancient, humble", "hook": "surprising_stat",
      "narration": "For most of history, there was no money...",
      "shots": [
        // shot_size: EST_WIDE|WIDE|MEDIUM|CLOSE|DETAIL ; camera_move: static|push_in|
        // pull_out|pan|tilt|parallax (flat-safe only) — VARY per adjacent beat, static for payoff
        {"id": "a", "dur": 5, "title": true,  "shot_size": "WIDE", "camera_move": "push_in",
         "scene": "...wide establishing collage...",
         "element_motion": "traders gesture, goat bobs, a paper bird flaps across the frame, coins scatter"},
        {"id": "b", "dur": 5, "title": false, "shot_size": "CLOSE", "camera_move": "parallax",
         "scene": "...close cut-in detail...",
         "element_motion": "the exchanged goods slide together, halftone pulses"}
      ]
    }
  ]
}
```
`theme`+`arc` set the two big layers; `element_motion` per shot is the energy (make it rich — see
below). `motion`/`collage_style`/`era` are still read for back-compat.

## Model selection (always verify IDs live)

Model IDs change — fetch the live list first: `GET https://api.atlascloud.ai/api/v1/models`
(no auth; keep only `display_console: true`). Defaults that work today:

| Job | Model | Note |
|---|---|---|
| Keyframe / collage poster | `google/nano-banana-2/text-to-image` | default; renders CN+EN text well; `image_resolution` 1k/2k/4k |
| Keyframe (alternative) | `openai/gpt-image-2/text-to-image` | set via `image_model`; size+quality auto-mapped from aspect+resolution |
| Cut out an element | `youchuan/v8.1/remove-background` | advanced path only |
| Animate (non-real content) | `google/gemini-omni-flash/image-to-video` | keeps text stable, layered motion |
| Animate (**real people / brands**) | `kwaivgi/kling-video-o3-pro/image-to-video` | Omni & Seedance BLOCK celebrities |
| Narration | `xai/tts-v1` | clean, multilingual, `voice_id` |
| Music | `minimax/music-2.6` | `is_instrumental: true` |

See `references/models-and-gotchas.md` for the full model-choice reasoning and every
API / ffmpeg gotcha (auth header, curl downloads, no-libass captions, content blocks, etc.).
Read it before debugging any failure — most failures are already documented there.

**Backends are pluggable.** Every API call goes through a **provider** (`scripts/provider.py`);
Atlas Cloud is the default and only backend today. Set `"provider"` in beats.json to route to a
different backend once one is added — the stage scripts don't change. `scripts/provider.py`'s
`run_jobs()` also does the submit/poll with **auto-resubmit on a stalled or failed job**.

## Advanced: element-level motion collage

The standard path animates the *whole* poster (great, automated, "living poster"). For the
dramatic **pieces-fly-in-and-assemble** motion collage (à la cr7v2), or to animate **real
people with full control and zero content filters**, cut each poster into independent
elements and drive them with the local keyframe engine (no video model needed).

Read `references/local-engine.md`. In short: `extract_elements.py` (crop + background-removal
+ residue/erase cleanup) → `motion.py` (Layer + keyframes, `fly_in`/`slap`/`drop`/`pop_settle`
easings, procedural confetti/starburst, camera zoom+shake+whip, frame render). Pieces fly
back to their **original positions** on a blurred-placeholder backdrop, so the assembled
frame reconstructs the original poster.

## Editions

- **Auto edition** (this skill): topic in, film out, all on Atlas.
- **Manual prompt-pack**: if the user isn't on Atlas, just produce the beat map + the per-beat
  image prompts + the per-clip motion prompts + the narration script for them to paste into
  any generator. The creative engine (the prompts) is identical.
