# Host mode — a presenter speaks on camera

A **host shot** (`"kind": "host"`) cuts to a presenter who speaks the beat's narration,
lip-synced, standing inside the paper-collage world. The input is ONE still image of the
presenter (a finished character design). It is not A-roll (that needs a real recorded
video) and not C-roll (a silent photo sticker).

Validated on the 60s "A Brief History of Silicon Valley" film (two host beats) and re-tested
on 16:9 and 9:16 when this mode was added.

## Why two plates

No single model gives lip-sync + a stable face + a moving background. Seedance lip-syncs
and holds the likeness but re-invents the background; Omni moves flat paper best but takes
no audio. So each host shot is two plates, generated separately and keyed together:

| Plate | Still | Video |
|---|---|---|
| **Person** | presenter on flat chroma green `#00B140` (`nano-banana-2/edit`) | `seedance-2.0/reference-to-video`, driven by the beat's narration |
| **World** | the collage with the presenter's area left empty, no people (`nano-banana-2/text-to-image`, same theme as the film) | `gemini-omni-flash/image-to-video`, camera locked |

Then `colorkey` + `despill` and `overlay=0:0`. Both plates share one framing, so no
repositioning is needed.

## Workflow

```
beats.json -> audio.py -> keyframes.py (skips host) -> host_plates.py -> LOOK at the plates
           -> host_clips.py (prints a cost estimate; re-run with --yes) -> clips.py (skips host) -> assemble.py
```

- `audio.py` must run first: the beat's narration is the reference audio.
- `host_plates.py <project> [ids] [--redo]` — two stills per shot (~$0.24). **Check them
  before paying for video**: flat even green, the face is the presenter's and not a redraw,
  nothing in the world plate's empty region, the presenter where you want them.
- `host_clips.py <project> [ids] [--yes] [--redo]` — spends money. Without `--yes` it only
  prints the plan and an estimate; show that to the user first. Clips already on disk are
  reused. To regenerate only one plate's video, delete its `person_clip_path` or
  `world_clip_path` from beats.json.
- `lipsync_score.py <audio> <video> [--mouth x,y,w,h]` — optional QA (needs numpy).

## beats.json

```jsonc
"host": {
  "avatar": "path/to/presenter.jpg",   // a FINISHED character design, never redrawn (str or list)
  "subject": "woman",                  // optional noun for prompts, default "presenter"
  "outfit": "a cream ivory zip-up hoodie",   // optional, locks clothing so the body does not drift
  "position": "left",                  // where they stand; see Layouts
  "size": 0.25,                        // head height / frame height, 0.08-0.6
  "person_video_model": "bytedance/seedance-2.0/reference-to-video",   // optional
  "world_video_model": "google/gemini-omni-flash/image-to-video"       // optional
},
"beats": [{
  "id": 1, "narration": "...", "feel": "bright, curious",
  "shots": [{
    "id": "a", "kind": "host", "title": false,
    "scene": "WORLD plate only: low torn-paper hills, a big sun disc, ... (no people)",
    "element_motion": "WORLD motion: name EVERY element and pin its shape"
  }]
}]
```

A host beat has exactly ONE shot (the presenter speaks the whole beat) and its narration
must be **at most 9.5 s** (the clip is `ceil(narration + 0.5)` seconds and Omni is verified
up to 10 s). Split longer lines into two beats. `scene` and `element_motion` describe the
world only; do not mention the presenter's area in `scene`, the script adds it.

## Layouts and adjusting the presenter

The frame spec lives in one table, `HOST_LAYOUTS` in `scripts/host.py`:

| Aspect | `position` choices | Default | Notes |
|---|---|---|---|
| 16:9 | `left`, `center`, `right` | `left`, head 0.25 | validated |
| 9:16 | `lower` | `lower`, head ~1/7 | validated once (6 s) |

`size` is a hint, not a measurement: asked for 1/7 on 9:16 the model drew about 1/5. Check
the person plate and adjust. Custom `position`/`size` means the default mouth box of
`lipsync_score.py` no longer applies; pass `--mouth`. Other aspect ratios are rejected with
a pointer to the table. To add one: a new entry (regions, placement and world-clear
templates, mouth box) plus one validation run. Omni image-to-video only accepts 16:9 and
9:16, so 1:1 and 4:3 need a different world-video model or a crop.

## Rules (each earned by a failed run)

1. **The audio fed to Seedance must equal the requested video length exactly.** The script
   pads with silence. Shorter audio makes the mouth drift across the whole clip.
2. **The beat's audio becomes the model's OWN output track**, extracted and normalised to
   -18 LUFS. Seedance re-times the reference audio (best lag +0.08 s against its own track,
   -0.44 s against the original narration), and the error is not a constant shift. The
   original is kept as `narration_audio_reference`.
3. **One reference image only.** Two images (green plate + studio portrait) scored 0.033
   against 0.095 for one.
4. **Lock the camera on both plates.** If one moves, the composite slides apart.
5. **Pin each world element's shape** in `element_motion` ("the plane stays the same
   propeller plane"). "Add nothing new" alone does not stop Omni morphing things.
6. **Host shots are never time-stretched.** Their audio is their clip; `assemble.py` skips
   the `narration + 0.5 s` extension and the slow-down for `kind: "host"`.

## Known limits

- **World-video drift.** Even with shapes pinned, Omni sometimes re-renders the world: in
  both 2026-10 tests the paper trees turned photographic, colours shifted, clouds appeared
  and one frame grew a stray face at the top edge. The sun and plane held shape in one run
  and not in the other. A shorter clip did not fix it. Re-roll (delete `world_clip_path`),
  simplify the world plate, or try another `world_video_model`.
- Validated only with a semi-real illustrated digital-human design. A raw real-person selfie
  is untested and may be refused.
- The host beat speaks the model's rendition of the narration while neighbouring beats speak
  the TTS voice; the timbre match across that cut is not measured.
- Seedance has the lowest phoneme fidelity of the models tried (correlation 0.246 vs
  InfiniteTalk 0.503, Kling 0.460, OmniHuman 0.422, on one plate). It was kept for
  expression and likeness. A best-lag near 0 with low correlation means model limit; a
  non-zero lag means a timing bug you can fix.
- A host clip is ~$0.36 per second (Seedance 720p ~$0.194, Omni $0.13, two stills $0.24 per
  shot) against ~$0.16 for B-roll; with `seedance-2.0-fast` the person part is roughly a
  third. Prices are from 2026-07-30 official pages: verify before relying on them.
- The mixed loudness of a -18 LUFS host track plus `assemble.py`'s final gain can clip;
  lower `mix.voice` / `mix.music` in beats.json if the master peaks above 0 dB.
