# Contributing to Vox Director

Thanks for helping out! Vox Director is an agent skill: a set of Python stage
scripts plus the docs (`SKILL.md`, `references/`) that tell an agent how to drive
them. Both halves matter: a prompt or a doc change can affect the output as much
as a code change.

This guide covers how changes get in, what to check before opening a pull
request, and the house rules that keep generated films consistent and API costs
under control.

- [Ways to contribute](#ways-to-contribute)
- [Before you start](#before-you-start)
- [Development setup](#development-setup)
- [Making changes](#making-changes)
- [Validating your change](#validating-your-change)
- [Keeping docs and the skill bundle in sync](#keeping-docs-and-the-skill-bundle-in-sync)
- [Commits and pull requests](#commits-and-pull-requests)
- [Reporting bugs and requesting features](#reporting-bugs-and-requesting-features)
- [Security](#security)
- [License](#license)

## Ways to contribute

- **Bug fixes**: pipeline failures, ffmpeg edge cases, platform issues.
- **Theme presets**: a new look in `styles.THEME_PRESETS` with a validated bake-off.
- **Provider backends**: a new media backend behind `scripts/provider.py`.
- **Modes and stages**: larger features like A-roll, C-roll or host mode. Open an
  issue first (see below).
- **Docs**: corrections, clearer instructions, and keeping the Chinese docs in sync.
- **Examples**: `beats.json` files in `examples/` that show a pattern well.

## Before you start

1. **Search [issues](https://github.com/Alisa0808/vox-director/issues) and
   [pull requests](https://github.com/Alisa0808/vox-director/pulls)**, including
   open ones. Several provider backends and fixes are already in flight, so
   build on or review those instead of duplicating them.
2. **Open an issue before large work**: a new mode, a new provider, a change to
   the `beats.json` schema, or anything that changes the default look or default
   models. Agreeing on the approach first saves you paid validation runs on a
   design that won't be merged.
3. Small fixes (typos, an obvious bug, a doc correction) can go straight to a PR.

## Development setup

Requirements (same as running the skill):

- Python 3.10 or newer, with Pillow (`pip install pillow`). `numpy` is only
  needed for the optional QA tool `lipsync_score.py` and the `erase` option of
  `extract_elements.py`.
- `ffmpeg` and `ffprobe` on your `PATH`.
- `curl` (used for uploads and downloads).
- An Atlas Cloud API key in `ATLASCLOUD_API_KEY`
  (<https://www.atlascloud.ai/console/api-keys>), but only for stages that call
  the API. Many changes can be developed and checked without one; see
  [Validating your change](#validating-your-change).

Fork the repo on GitHub, then:

```bash
git clone https://github.com/<your-username>/vox-director.git
cd vox-director
git remote add upstream https://github.com/Alisa0808/vox-director.git
git fetch upstream
git switch -c fix/short-description upstream/main
```

Keep your branch current with `git fetch upstream` followed by
`git rebase upstream/main`.

Projects you generate go under `out/<project>/`, which is git-ignored. Copy an
example to start: `examples/money-15s.beats.json` → `out/money-15s/beats.json`.

### Platform notes

The pipeline has been developed and validated on macOS. Linux and Windows have
known gaps today:

- Caption and watermark fonts are only looked up at macOS paths (`text_overlay.py`).
- `atlas_cloud.py` calls `/usr/bin/curl` directly.
- On Windows, `beats.json` is read and written with the system encoding rather
  than UTF-8. Set `PYTHONUTF8=1` until that's fixed.

On Windows the docs' `python3` is usually `python`. Fixes for these are very
welcome.

## Making changes

### Architecture rules

- **One stage per script, one `beats.json` per project.** A stage reads
  `beats.json`, does its work, and writes its results back (`keyframe_url`,
  `clip_path`, `narration_audio`, …). That makes every stage resumable. New
  stages should skip work that's already done, not redo it.
- **Media API calls go through the provider layer.** Use
  `get_provider(doc.get("provider"))` and `run_jobs()` rather than calling
  `atlas_cloud` from a stage. A new backend is a `Provider` subclass plus one
  `_REGISTRY` entry in `scripts/provider.py`; the stage scripts shouldn't change.
- **Keep dependencies minimal.** The core pipeline is standard library + Pillow,
  with ffmpeg called through `subprocess`. Discuss before adding a pip
  dependency.
- **Write cross-platform code.** Open text files with `encoding="utf-8"`, build
  paths with `os.path`, and find executables with `shutil.which()` rather than
  hard-coded paths.

### Cost and safety rules

These protect the user's money and their right to decide:

- **Keep the human approval gates.** The beat map review, the aspect-ratio
  approximation confirm (`aspect_approx_confirmed`) and the host-mode cost
  estimate (`--yes`) exist on purpose. Don't bypass or weaken them.
- **Don't add silent retries of billable requests.** Generation POSTs aren't
  retried, since each one creates a billable task. Polling GETs are safe to retry.
- **Gate new expensive stages.** A stage that can spend significant money
  should print an estimate and require explicit confirmation, like
  `host_clips.py`.

### Prompts are load-bearing

Much of the wording in the prompt templates (`styles.py`, `clips.py`,
`croll_keyframes.py`, `aroll_clips.py`, `host.py`) is there because a specific
generation failed without it. The comments next to them record what went wrong.

- Don't reword a validated prompt for style alone.
- If you change one, say in the PR which failure it fixes and show a before and
  after run.
- Keep the *why* comment next to the wording, with the date you validated it.
- Use neutral pronouns (*they/their*) in prompt templates.

### Code style

Match the surrounding code: a module docstring with a `Usage:` line, a
`run(project_dir, ...)` entry point, f-strings, and comments that explain *why*
rather than *what*. There's no linter or formatter in the repo, so keep diffs
focused and don't reformat code you aren't changing.

### Secrets, media and likeness

- Never commit API keys or `.env` files. The `.gitignore` covers the common
  names, but check `git diff --staged` before committing.
- Don't commit generated projects (`out/`) or large media. The README's
  showcase videos are hosted as GitHub attachments, not stored in the repo.
- Only commit photos, voice samples or likenesses you have the right to share.
  C-roll anchors and `voice.clone_ref` samples of real people stay out of the
  repo unless they consented.

## Validating your change

There's no CI and no automated test suite on `main` yet, so your PR description
is the test report. Split it the way reviewers expect: what you checked
**offline** (free) and what you checked with **paid** API calls.

### Always (offline)

```bash
python -m compileall -q scripts
```

This catches syntax errors in every script (exit code 1 on failure) and works
the same in Bash and PowerShell.

### Offline checks worth doing

- **Assembly and ffmpeg changes:** re-run `assemble.py` (or
  `aroll_assemble.py`) on a project that already has clips and audio. It's free.
  Compare the output duration and a few frames before and after:

  ```bash
  ffmpeg -ss 3 -i out/<project>/final.mp4 -vf "scale=640:-1,format=yuvj420p" -frames:v 1 frame.jpg
  ```

- **Prompt-template refactors:** show that the default prompts are
  byte-identical to before, unless changing them is the point.
- **Pure logic** (ASR segmentation, aspect routing, prompt composition,
  `run_jobs`): unit-test it offline with the standard library's `unittest`. Put
  tests under `tests/` and run `python -m unittest discover -s tests`. New tests
  are very welcome.

### Paid validation

Changes to prompts, models, model parameters or a provider need at least one
real run. Keep it small: one beat, the shortest duration, `1k` images and `720p`
video. In the PR, list what you generated, which models, the outcome, and
roughly what it cost. Attach a frame or a short clip (GitHub attachments are
limited to 10 MB).

## Keeping docs and the skill bundle in sync

| If you change… | Also update… |
|---|---|
| The workflow, a stage's usage, or `beats.json` fields | `SKILL.md` (steps + schema) **and** `SKILL.zh.md` |
| User-facing features or the showcase | `README.md` **and** `README.zh.md` |
| A model, a model parameter, or an API/ffmpeg workaround | `references/models-and-gotchas.md` |
| Prompt structure or theme presets | `references/prompt-guide.md` (and the preset list in `SKILL.md`) |
| Voices | `references/voices.md` |
| Host mode | `references/host-mode.md` |
| Anything in `SKILL.md`, `references/`, `examples/` or `scripts/` | Rebuild `vox-director.skill` (below) |

If you can't write the Chinese update yourself, say so in the PR and a
maintainer or another contributor can help.

The `description` in `SKILL.md`'s frontmatter is what agents use to decide when
to load the skill. Keep it under the 1024-character limit for skill
descriptions (it's about 990 now).

### Rebuilding `vox-director.skill`

The `.skill` file is a stored (uncompressed) zip of `SKILL.md`, `references/`,
`examples/` and `scripts/` under a `vox-director/` folder. Stage your changes,
then build it from the staged files so the bundle matches exactly what you're
committing:

```bash
git add -A
git -c core.autocrlf=false archive --format=zip -0 --prefix=vox-director/ -o vox-director.skill $(git write-tree) SKILL.md references examples scripts
git add vox-director.skill
```

The same command works in PowerShell. `core.autocrlf=false` keeps Windows line
endings out of the bundle.

## Commits and pull requests

- **One concern per PR.** If you notice unrelated problems, list them under
  "Not in this PR" rather than fixing everything at once.
- **Branch names:** `feat/…`, `fix/…`, `docs/…`, `refactor/…`, `chore/…`.
- **Commit messages and PR titles** follow
  [Conventional Commits](https://www.conventionalcommits.org/): `type: short
  imperative summary`, for example `fix: rebuild the skill bundle with LF line
  endings`. PRs are squash-merged and **the PR title becomes the commit
  message**, so make it a good one.
- **Fill in the PR template:** what changed and why, offline and paid
  validation, known issues, and what's deliberately not included. Link the issue
  it closes (`Fixes #123`).
- **Open a draft PR early** for bigger work. It's the easiest way to get
  feedback on direction.
- **AI-assisted contributions are welcome.** Say so in the PR, and review and
  test the output yourself: you're responsible for what you submit.
- **Credit collaborators** with a `Co-authored-by:` trailer or a credits line in
  the PR description.

## Reporting bugs and requesting features

Use the issue forms. For bugs, the most useful details are:

- the exact command you ran and its full output;
- the relevant part of your `beats.json`, with secrets removed;
- the model IDs involved, plus any prediction or job IDs from the output;
- your OS, Python version, and the first line of `ffmpeg -version`.

Check `references/models-and-gotchas.md` first. Many API and ffmpeg failures
are already documented there with a fix.

**Never post your `ATLASCLOUD_API_KEY`** in an issue, a log or a screenshot. If
you do by accident, revoke it in the Atlas Cloud console right away.

## Security

If you find a security problem, for example a way the scripts could leak an
API key, please don't open a public issue. Use GitHub's private vulnerability
reporting (**Security → Report a vulnerability**) if it's enabled on the repo.
Otherwise, contact the maintainer privately before sharing details publicly.

## License

By contributing, you agree that your contributions are licensed under the
project's [MIT License](LICENSE).
