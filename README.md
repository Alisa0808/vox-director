<p align="right"><b>English</b> · <a href="README.zh.md">简体中文</a></p>

# 🎬 Vox Director

**Turn one topic into a finished Vox-style paper-collage explainer / ad video — script, collage keyframes, motion, voice-over, music and captions, all automated.**

An **agent skill** that runs end to end on the [Atlas Cloud](https://www.atlascloud.ai/?utm_source=github&utm_campaign=vox_director) API + local `ffmpeg`, usable by any coding agent (Claude Code, Codex, etc.). You give it a one-line topic; it gives you an `mp4`.

![License: MIT](https://img.shields.io/badge/License-MIT-black.svg) ![Powered by Atlas Cloud](https://img.shields.io/badge/powered%20by-Atlas%20Cloud-ff5a1f.svg) ![Agent Skill](https://img.shields.io/badge/Agent-Skill-d97757.svg)

<div align="center">

https://github.com/user-attachments/assets/ed08d230-7bcb-4b48-a17d-23c079208f9f

<b>▶ "The evolution of Chinese civilization" · 30s</b>

</div>

<table>
  <tr>
    <td width="33%"><a href="https://github.com/user-attachments/assets/216cd62f-6314-456c-94cf-1090b8559a22"><img src="assets/thumbs/football.jpg" width="100%" alt="How football conquered the world"></a></td>
    <td width="33%"><a href="https://github.com/user-attachments/assets/561788b1-5615-4828-b3f8-b24ae5ad7bcd"><img src="assets/thumbs/mexican.jpg" width="100%" alt="Mexican street food"></a></td>
    <td width="33%"><a href="https://github.com/user-attachments/assets/f69f072f-f50a-41ba-9e66-7ed0aae4ddc0"><img src="assets/thumbs/money.jpg" width="100%" alt="A brief history of money"></a></td>
  </tr>
  <tr>
    <td align="center"><sub>Football history · 60s</sub></td>
    <td align="center"><sub>Mexican street food · 60s</sub></td>
    <td align="center"><sub>A brief history of money · 60s</sub></td>
  </tr>
</table>

<p align="center"><sub><em>▶ more films — click any thumbnail to play</em></sub></p>

---

## What it is

The look is the modern editorial **paper-collage** popularized by Vox explainers: hand-cut paper cut-outs, torn edges, tape, halftone dots, newspaper clippings, bold flat color per beat, big cut-out headlines — brought to life with motion, a narrator, music and captions.

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

This is an **agent skill** — it works with any coding agent that can read a workflow and run scripts (Claude Code, Codex, …). Claude Code auto-discovers it as a skill; other agents read [`AGENTS.md`](AGENTS.md) → [`SKILL.md`](SKILL.md).

**Option A — from this repo:**
```bash
git clone https://github.com/Alisa0808/vox-director.git ~/.claude/skills/vox-director
```

**Option B — from the packaged skill:** download [`vox-director.skill`](vox-director.skill) and install it via your Claude skills UI.

Then set your Atlas Cloud API key (get one at [atlascloud.ai/console/api-keys](https://www.atlascloud.ai/console/api-keys?utm_source=github&utm_campaign=vox_director)):
```bash
export ATLASCLOUD_API_KEY="sk-..."
```

## Quick start

Just ask your coding agent, with the skill installed:

> *"Make me a Vox-style collage video introducing Mexican street food — English, 16:9, 15 seconds."*

The agent will draft a beat map for your approval, run a style bake-off for you to pick from, then generate keyframes → motion → voice → music and assemble `out/<project>/final.mp4`.

## Requirements

- A **coding agent** — Claude Code, Codex, or similar
- **Atlas Cloud** API key
- **ffmpeg** + **ffprobe** (`brew install ffmpeg`)
- **Python 3** with **Pillow** (`pip install pillow`) — for caption/watermark overlays

## What's in the box

```
SKILL.md              the skill (English) — the workflow the agent follows
SKILL.zh.md           the same skill in Chinese
AGENTS.md             entry point for non-Claude agents (Codex, …)
references/           the creative engine
  prompt-guide.md       the LOOK layer — prompt structures, vocab & 8 theme presets
  beat-layer.md         14 narrative arcs + hook/pacing + shot patterns
  voices.md             xai/tts voice roster — pick a voice_id per language/tone
  models-and-gotchas.md every API / ffmpeg gotcha, already solved
  local-engine.md       the advanced element-level motion engine
scripts/              one script per pipeline stage
examples/             ready-to-run beats.json examples
assets/               the showcase film
```

## Credits

Inspired by the collage-ad workflows of **[Stav Zilber](https://x.com/StavZilber)**, **[rom1trs](https://x.com/rom1trs)** and **[Higgsfield](https://x.com/higgsfield_ai)**, and by **[Vox](https://www.vox.com)**'s explainer visual language.

Built end to end on **[Atlas Cloud](https://www.atlascloud.ai/?utm_source=github&utm_campaign=vox_director)** — one prompt, one film.

## License

[MIT](LICENSE) © 2026 Atlas Cloud
