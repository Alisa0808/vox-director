<!--
Thanks for contributing! See CONTRIBUTING.md for the full guide.
PR title: `type: short imperative summary` (feat, fix, docs, refactor, chore).
PRs are squash-merged, so the title becomes the commit message.
-->

## What

<!-- What does this change, and why? Link the issue it closes, e.g. "Fixes #123". -->

## Validation

**Offline (free)**

- [ ] `python -m compileall -q scripts` passes
- <!-- e.g. re-ran assemble.py on an existing project; unit tests; default prompts byte-identical -->

**Paid** (needed if prompts, models, model parameters or a provider changed)

<!-- What you generated, which models, the outcome, and roughly what it cost.
Attach a frame or a short clip (GitHub attachments max 10 MB). Write "n/a" if nothing paid was needed. -->

## Checklist

- [ ] Docs updated where needed: `SKILL.md` ↔ `SKILL.zh.md`, `README.md` ↔ `README.zh.md`, `references/`
- [ ] `vox-director.skill` rebuilt if `SKILL.md`, `references/`, `examples/` or `scripts/` changed
- [ ] No API keys, `.env` files, `out/` projects or large media committed
- [ ] Approval gates and cost confirmations still work (beat map, aspect confirm, `--yes`)

## Known issues / not in this PR

<!-- Anything you noticed but left out on purpose, or limits of what you validated. -->
