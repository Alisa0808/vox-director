<p align="right"><b>English</b> · <a href="README.zh.md">简体中文</a></p>

# 🎬 Vox Director

**Turn one topic into a finished Vox-style paper-collage explainer / ad video — script, collage keyframes, motion, voice-over, music and captions, all automated.**

A [Claude](https://claude.com/claude-code) skill that runs end to end on the [Atlas Cloud](https://www.atlascloud.ai) API + local `ffmpeg`. You give it a one-line topic; it gives you an `mp4`.

![License: MIT](https://img.shields.io/badge/License-MIT-black.svg) ![Powered by Atlas Cloud](https://img.shields.io/badge/powered%20by-Atlas%20Cloud-ff5a1f.svg) ![Claude Skill](https://img.shields.io/badge/Claude-Skill-d97757.svg)

https://github.com/user-attachments/assets/ed08d230-7bcb-4b48-a17d-23c079208f9f

<p align="center">
  <em>"The evolution of Chinese civilization" — one topic in, this out. ▶ <a href="https://github.com/Alisa0808/vox-director/blob/main/assets/showcase-tang.mp4">Trouble playing the video? Watch it here</a>.</em>
</p>

---

## What it is

The look is the modern editorial **paper-collage** popularized by Vox explainers and creators like Stav Zilber and rom1trs: hand-cut paper cut-outs, torn edges, tape, halftone dots, newspaper clippings, bold flat color per beat, big cut-out headlines — brought to life with motion, a narrator, music and captions.

Vox Director fuses three workflows into one repeatable pipeline:

| Source | Contribution |
|---|---|
| **Stav Zilber** (original) | interview-style product ads · Omni Flash paper/collage motion engine · end-frame link · reference-image consistency · narration discipline |
| **rom1trs / Remotion** | code-rendered Vox visuals (text & data stay razor-sharp) |
| **Higgsfield Explainer** | auto-research a topic · any-language narration · long-form explainers |

## How it works

One topic flows through one script per stage, all driven by a single `beats.json` per project:

```
topic
  │
  ├─ 1. beat map        pick a narrative arc → write beats.json      ◀── GATE 1: you approve the beat map
  ├─ 2. style bake-off  render the same beat in 3–4 themes           ◀── GATE 2: you pick the look by eye
  ├─ 3. keyframes       one collage poster per beat  (nano-banana-2)
  ├─ 4. motion          animate each poster          (gemini-omni-flash i2v)
  ├─ 5. voice + music   one narrator (xai/tts) + BGM (minimax/music)
  ├─ 6. assemble        ffmpeg: concat, duck music under VO, burn captions + watermark
  └─ final.mp4
```

Two ideas make or break the result, and the skill is built around both:

1. **The look is born in the image step.** Each beat is a finished collage *poster*. All the collage DNA (torn paper, cut-outs, halftone, headline text) lives in that image — if the poster isn't a rich collage, nothing downstream saves it.
2. **The motion is added after.** By default an AI video model animates the whole poster (the "living poster" path). For dramatic *piece-by-piece* assembly, an optional local keyframe engine cuts the poster into parts and drives them frame-by-frame (no content filters, pixel-exact — great for real people).

Two human decision gates keep you in control (approve the beat map; pick the style); everything else is automated.

## Models (verified on Atlas Cloud)

| Job | Model |
|---|---|
| Keyframe / collage poster | `google/nano-banana-2/text-to-image` |
| Animate (non-real content) | `google/gemini-omni-flash/image-to-video` |
| Animate (**real people / brands**) | `kwaivgi/kling-video-o3-pro/image-to-video` |
| Narration | `xai/tts-v1` |
| Music | `minimax/music-2.6` |
| Cut out an element (advanced path) | `youchuan/v8.1/remove-background` |

Model IDs drift — the skill fetches the live list from `GET https://api.atlascloud.ai/api/v1/models` before running.

## Install

This is a Claude skill (works in Claude Code and Claude apps that support skills).

**Option A — from this repo:**
```bash
git clone https://github.com/Alisa0808/vox-director.git ~/.claude/skills/vox-director
```

**Option B — from the packaged skill:** download [`vox-director.skill`](vox-director.skill) and install it via your Claude skills UI.

Then set your Atlas Cloud API key (get one at <https://www.atlascloud.ai/console/api-keys>):
```bash
export ATLASCLOUD_API_KEY="sk-..."
```

## Quick start

Just ask Claude, with the skill installed:

> *"Make me a Vox-style collage video about the history of money — English, 9:16, 60 seconds."*

Claude will draft a beat map for your approval, run a style bake-off for you to pick from, then generate keyframes → motion → voice → music and assemble `out/<project>/final.mp4`.

## Requirements

- **Claude** with skills (e.g. Claude Code)
- **Atlas Cloud** API key
- **ffmpeg** + **ffprobe** (`brew install ffmpeg`)
- **Python 3** with **Pillow** (`pip install pillow`) — for caption/watermark overlays

## What's in the box

```
SKILL.md              the skill (English) — the workflow Claude follows
SKILL.zh.md           the same skill in Chinese
references/           the creative engine
  prompt-guide.md       image + video prompt structures
  vocab-bank.md         8 image dims + 9 video axes + 8 theme presets
  beat-layer.md         14 narrative arcs + hook/pacing + shot patterns
  models-and-gotchas.md every API / ffmpeg gotcha, already solved
  local-engine.md       the advanced element-level motion engine
scripts/              one script per pipeline stage
examples/             ready-to-run beats.json examples
assets/               the showcase film
```

## Credits

Inspired by the collage-ad workflows of **[Stav Zilber](https://x.com/StavZilber)**, **[rom1trs](https://x.com/rom1trs)** and **[Higgsfield](https://x.com/higgsfield_ai)**, and by **[Vox](https://www.vox.com)**'s explainer visual language.

Built end to end on **[Atlas Cloud](https://www.atlascloud.ai)** — one prompt, one film.

## License

[MIT](LICENSE) © 2026 Atlas Cloud
