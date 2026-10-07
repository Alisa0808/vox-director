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

- `ATLASCLOUD_API_KEY` in the environment — https://www.atlascloud.ai/console/api-keys
- `ffmpeg` + `ffprobe`
- Python 3 with `pillow`

## Agent notes

- **Claude Code** auto-loads this as a skill from `SKILL.md`'s frontmatter — just
  ask for a "vox video".
- **Codex / other agents**: follow `SKILL.md` as your instructions; this
  `AGENTS.md` is your entry point.

## Changing this repo (for the agent)

If you are modifying the skill itself rather than using it, follow
**`CONTRIBUTING.md`**: keep `SKILL.md`/`SKILL.zh.md` and both READMEs in sync,
rebuild `vox-director.skill`, and report offline and paid validation separately
in the pull request. Never weaken the human approval gates or add silent retries
of billable API calls.
