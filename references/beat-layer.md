# Beat / Shot Layer Library — narrative arc + per-shot spec

The counterpart to `prompt-guide.md` (which covers the LOOK / theme layer). This covers the
**beat layer**: the narrative skeleton across the whole film + the per-shot spec (shot size,
camera move, element motion). Distilled from short-form/story-structure/editing research
(sources at bottom). One "poster per beat"; our per-shot unit ≈ what the sources call a beat.

Three tiers, three control methods (this is the design):
- **Narrative arc** → preset menu, AI recommends from topic, **user confirms** (one click).
- **Per-beat scene + headline** → AI drafts from the topic, **user approves/edits** (the one mandatory gate).
- **Shot size + camera move** → **rule/preset-derived from arc position + anti-monotony**; AI fills from a *hard-constrained* vocab; user can override but rarely needs to. Never free-form (the model will emit "orbit"/"dolly-zoom" and break the flat art).

---

## 1. Narrative Arc Library (pick one; AI recommends by topic)

| Arc (token) | When to use | Beat shape |
|---|---|---|
| `hook_payoff` | default for any single idea; safest | Hook → Context → Build → Payoff → Button |
| `pas` | pain-aware ads, urgency | Problem → Agitate → Solve → Proof → CTA |
| `bab` | when the "after" sells better than the pain | Before → After → Bridge → CTA |
| `aida` | cold-audience paid ads | Attention → Interest → Desire → Action |
| `storybrand` | brand/service, customer-as-hero | Hero wants → Problem → Guide → Plan → CTA → stakes |
| `how_it_works` | product/process/system explainer | Hook → What it is → 2–3 shown steps → Benefit → CTA |
| `timeline` | history, "evolution of", journeys | Start → event → event → turning point → present → takeaway |
| `man_in_hole` | case study, comeback, transformation (highest-rated arc) | OK → fall → deepen → climb out → better than before |
| `story_spine` | mission/brand/founder tales | Once… → Every day… → Until one day… → Because… → Until finally… → Ever since… |
| `origin` | founder / "why we exist" | World → spark → leap → struggle → breakthrough → today |
| `myth_buster` | correct a misconception | FACT first → the myth → expose fallacy → what to believe → CTA |
| `listicle` | tips/tools/rankings "N ways to…" | Promise → item → item → … → #1 → recap/CTA |
| `three_act` | any narrative 60s piece | Setup → Confrontation (rising) → Resolution |
| `story_circle` | character-driven UGC/brand | You → Need → Go → Search → Find → Take → Return → Change |

**Topic → arc heuristic:** product/service ad → `pas`/`bab`/`aida`/`storybrand`; concept/system →
`how_it_works`/`hook_payoff`; historical/"evolution of" → `timeline`; transformation/case study →
`man_in_hole`; brand/mission → `story_spine`/`origin`; correcting a belief → `myth_buster`;
ranking/tips → `listicle`.

## 2. Hook · Pacing · Beat-count (firm presets)

- **Hook in ≤3s** — ~65% of viewers decide by 3s. Beat 1's baked headline must carry the
  payoff-promise (bold claim / provocative question / surprising stat / "you're doing X wrong").
  Never spend beat 1 on setup.
- **Hook patterns (pick one for beat 1):** `mistake_callout · pain_point · surprising_stat ·
  direct_question · urgent_warning · secret_reveal · experiment_story · pattern_interrupt ·
  outcome_tease`. Underlying triggers: curiosity gap, pattern interrupt, bold claim.
- **Beat-count & length:**

  | Duration | Beats (posters) | Beat length | VO words |
  |---|---|---|---|
  | **30s** | 6–8 | ~4–5s | ~70–80 |
  | **60s** | 10–12 | ~5–6s | ~130–150 |

  (Our "beat×2 shots" model: ~6 beats × 2 shots = ~12 posters for 60s — matches.)
- **Proportions:** hook 1–3s → body 70–80% → payoff 10–20% → end/CTA 0–2s.
- **Change something visually every 3–5s; never hold a static poster >8s** → every beat needs
  internal motion (§3), which is why we split beats into short shots.
- **Endings:** `hard_cut` (on the payoff; default, drives rewatches) · `quick_cta` (≤2s, one
  action + benefit, 3–5 words) · `loop_close` (last line mirrors the first → seamless replay).

## 3. Shot-Pattern Library (per beat)

### Shot size (composition zoom of the poster)
`EST_WIDE` (whole scene/system, orient, scale) · `WIDE` (subject in environment) · `MEDIUM`
(one subject centered; workhorse) · `CLOSE` (one detail fills frame; emphasis/emotion) ·
`DETAIL`/`ECU` (single texture/word/number; a punch beat).
Coverage plays out **across beats** (we hold one poster per beat): move-in `EST_WIDE→MEDIUM→CLOSE`
(build intensity, peak on CLOSE) · move-out `CLOSE→…→WIDE` (reveal context; good ending) ·
**establishing-wide → detail cut-in** = the best 2-poster beat (a wide to orient, hard-cut to a
CLOSE of the key element — generate two posters for that beat).

### Camera move — HARD-CONSTRAINED flat-safe vocab
Rule: **uniform translate + uniform scale = safe** (text scales/moves as one piece);
**anything that warps perspective, blurs, or rotates text off-axis = banned.**

| ✅ safe (token) | realize on flat art | job | i2v phrasing |
|---|---|---|---|
| `static` | no transform, tiny element float | let a stat/quote land | "locked-off static, only subtle paper flutter, text fixed" |
| `push_in` | uniform scale-up (Ken Burns) | tension/focus | "very slow push in, text stays sharp and centered" |
| `pull_out` | uniform scale-down | reveal / big picture | "slow pull out revealing the full scene, flat, steady" |
| `pan` | translate across an over-wide poster | read a list/timeline | "slow horizontal pan, flat 2D, no perspective shift" |
| `tilt` | vertical translate | reveal scale / countdown | "slow vertical tilt, flat parallax, steady" |
| `parallax` | fg/mid/bg layers move at different speeds | the "living paper" signature | "subtle multi-layer parallax, paper layers drift at different speeds, 2.5D, flat" |
| `element` | one cut-out slides/hinges in, others still | introduce/emphasize one item | "one paper element slides in from edge, others static, stop-motion feel" |

**Bold / experimental (available, NOT banned):** `orbit`/`arc`, `dolly_zoom`, `roll/dutch`,
`whip`. Verified 2026-07-10 to *tend to* warp the flat art / smear text — but they're a **style
choice, not forbidden**. Use them with **`constraints: loose`** and **re-roll** until a
take lands; save them for a beat where the effect earns it. In `strict` mode the guards will
fight them (that's the point of the mode). `whip` also works well as a fast between-shot
transition. If you just want a dolly-in's *feel* cleanly, a 2D `push_in` scales text as one
piece and never warps.

### Element motion (what moves inside — a SEPARATE axis from camera) ⭐ THE ENERGY ENGINE
**We tested this on our own stack (2026-07-10) — it is where dynamism actually comes from, and
rich motion is SAFE.** A single collage keyframe animated with "the goat bobs, both traders
gesture, coins & shells scatter, AND a cut-out paper bird flaps across the whole frame" stayed
perfectly flat, text intact — and looked great. The Tang film already did this (paper crane
across frame). So **do NOT limit to one gentle verb.** `element_motion` is **AI's per-beat creative call — write
what actually fits THIS scene**, and make it rich (multiple things moving). It is safe to be bold.
Shot size gates it (WIDE → several elements move; CLOSE → that one thing animates strongly).
- **Encouraged (safe + punchy):** multiple elements move at once · coins/petals/scraps scatter &
  burst · elements pop/slide/flap/hinge in · drift · sway · flutter · pulse.
- **A "hero" traveling element** (a bird/plane/coin/arrow flying across the frame) is a great
  **occasional punch on a key beat — NOT every shot** (a flyer in every frame reads as a formula).
  Use it where it earns the moment; let most beats just move their own elements richly.
- **The ONLY real limits** (verified): keep it **rigid paper** (cut-outs slide/flap/scatter — no
  organic melting/`morph`/`warp`/body-horror), keep **text stable**, keep **flat 2D**.
- Camera and element motion are independent — one camera move + as much *element* motion as you like.

### Anti-monotony (biggest quality lever)
Every beat is a similar-looking poster, so **no two adjacent beats use the same camera move;
alternate families (scale ↔ translate ↔ static); reserve `static` for the payoff/quote beat** so
the motion drop signals "this is the point." Money-60s failed this (all 12 shots = push-in).

**Move-rhythm presets (drop-in per arc):**
- `hook_payoff` (8): push_in → pan → parallax → static → push_in → tilt → pull_out → static
- `pas`/`bab` (6): push_in → static → pan → parallax → push_in → static
- `listicle`: same move on every item (pan or tilt) but flip direction / parallax on #1; static on recap
- `timeline`: pan the same direction beat-to-beat (feels like moving through time) → push_in on the turning point → pull_out on the takeaway

## 4. Vocab tokens (copy-paste)

```
ARCS:  hook_payoff pas bab aida storybrand how_it_works timeline man_in_hole
       story_spine origin myth_buster listicle three_act story_circle
HOOKS: mistake_callout pain_point surprising_stat direct_question urgent_warning
       secret_reveal experiment_story pattern_interrupt outcome_tease
SIZES: EST_WIDE WIDE MEDIUM CLOSE DETAIL
MOVES: static push_in pull_out pan tilt parallax element   (BANNED: orbit arc crane boom
       pedestal dolly_zoom roll whip_pan handheld fast_zoom)
ENDINGS: hard_cut quick_cta loop_close
BEATS: 30s→6–8 @4–5s (~75w) · 60s→10–12 @5–6s (~140w) · hook ≤3s · change every 3–5s
```

## Sources (key)
Story structure: StudioBinder (three-act, story-circle, story-structure), Pixar story spine
(tckpublishing / sessionlab), Vonnegut shapes + Cornell 6-arc study (technologyreview). Ad
frameworks: AIDA/PAS/BAB (soarai, swiftcopy), StoryBrand (innatemarketinggenius), per-second ad
timing (benly.ai). Explainer/doc craft: Vox case studies (jasperpictures, storybench),
mypromovideos, Ken Burns (masterclass). Hook/pacing/retention: go-viral.app, prepublish.ai,
teleprompter.com, socialync.io, vidpros.com (clip length). Shots/coverage/editing: StudioBinder
shot sizes & camera movements, learnaboutfilm coverage/sequence, insidetheedit (pacing).
