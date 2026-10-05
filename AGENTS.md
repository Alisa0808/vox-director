# Vox Director — Agent Guide

This repository is an **agent skill**: a self-contained workflow that turns one
topic into a finished Vox-style paper-collage video (script → collage keyframes →
motion → voice-over → music → captions). It is not tied to any single assistant —
any coding agent that can read instructions and run scripts can drive it.

## How to use it (for the agent)

1. Read **`SKILL.md`** — the full workflow and the two human approval gates.
   (`SKILL.zh.md` is the same in Chinese.)
2. Before writing any prompt, read **`references/`** (prompt structures, the
   vocabulary/theme bank, and the narrative-beat library).
3. Work one project at a time under `out/<project>/`, driven by a single
   `beats.json`. Run the stages in **`scripts/`** in order:
   `style_bakeoff.py → keyframes.py → clips.py → audio.py → assemble.py`.

## Requirements

- An API key for the backend named in `beats.json` `"provider"`:
  - `atlas_cloud` (default) → `ATLASCLOUD_API_KEY` — https://www.atlascloud.ai/console/api-keys
  - `modelrunner` → `MODELRUNNER_API_KEY` — https://modelrunner.ai
- `ffmpeg` + `ffprobe`
- Python 3 with `pillow`

## Agent notes

- **Claude Code** auto-loads this as a skill from `SKILL.md`'s frontmatter — just
  ask for a "vox video".
- **Codex / other agents**: follow `SKILL.md` as your instructions; this
  `AGENTS.md` is your entry point.
