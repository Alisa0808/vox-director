# Voice roster — `xai/tts-v1` (pick a `voice_id` per film)

Set `voice.voice_id` in beats.json. **Pick by the film's LANGUAGE first, then match gender/tone
to the topic** — don't just leave the default.

- **Multilingual** voices (`ara eve leo rex sal`) speak ANY language — safe for English/Chinese/mixed.
- **Native** voices are optimized for their own language (more natural accent) and auto-cascade the
  `language` field.
- Skill default: **`leo`** (male, multilingual, documentary-ish). Override per film.

## Multilingual (any language)
| id | name | gender |
|---|---|---|
| `leo` | Leo | M — default |
| `rex` | Rex | M |
| `sal` | Sal | M |
| `ara` | Ara | F |
| `eve` | Eve | F |

## Native voices by language  (name · gender · id)
- **en** — Daniel · M · `96819d0bd28d` · James · M · `78a495fdbb39` · Grace · F · `f8cf5c2c78d4` · Claire · F · `79f3a8b96d43`
- **zh-CN** — Jian · M · `jpi39icg` · Hao · F · `d18jlf6v` · Xia · F · `33g9t0jl`
- **ja** — Ren · M · `b1a7441b97a1` · Sakura · F · `d0cb9ff07d95`
- **ko** — Jun-seo · M · `bf9fe5b5f981` · Min-jun · M · `b5ae17439907` · Ji-yeon · F · `23be42535a45` · Seo-yeon · F · `a0401c9101f8`
- **es** — Manuel · M · `yis75yfp` · Javier · M · `ekhwx401` · Andres · M · `0hhfxxqq` · Diego · `jupvcf34`
- **fr** — Remi · M · `0p0rt7o1` · Hugo · `hbxkrnwm` · Camille · F · `69smp8rm`
- **de** — Moritz · M · `41321eb41295` · Niklas · M · `40f31906b23d` · Clara · F · `458705c07139` · Lena · F · `3a7889066fa2`
- **it** — Enzo · M · `x7avnu1k` · Matteo · M · `bcs7l2c3` · Alessandro · M · `h27ltdnz` · Luca · F · `hqxr4yub`
- **pt** — Mateus · M · `abfbdf26f115` · Rafael · M · `3d030bc92a87` · Beatriz · F · `6da5baee46d0`
- **ru** — Dmitri · M · `wy0m9l5w` · Andrei · M · `dr8gqysu` · Pavel · M · `26w6ihxi` · Irina · F · `om17cury`
- **hi** — Karan · M · `89q2pnko` · Ananya · F · `73xd5dum`
- **ar** — Khalid · M · `70013edeb8e8` · Tariq · M · `23468361b4ef` · Layla · F · `35c8d7f60dc8`
- **tr** — Emre · M · `670a0c3ac005` · Kaan · M · `182a91893636` · Aylin · F · `d634b6da3d3b`
- **vi** — Duc · M · `fc7de6afcf6c` · Minh · M · `7a9ee820b342` · Mai · F · `0895a5b8ce5c`
- **th** — Aroon · M · `4ff93971bfdc` · Krit · M · `908c4626660f`
- **nl** — Thijs · M · `a13662ba951c` · Ruben · M · `244e27b39200` · Femke · F · `58d27475085e` · Noor · F · `247783ebdd51`
- **pl** — Jakub · M · `2badb5f46b1e` · Mateusz · M · `37329fd8895a` · Aleksandra · F · `1b12d5daee6b` · Katarzyna · F · `97fabd54445f`
- **sv-SE** — Axel · M · `e22152e06fd8` · Erik · M · `1f046a033914` · Saga · F · `490ea3be50b1`
- **da** — Kasper · M · `0ih5oi34` · Lars · M · `gwnexu6y` · Ida · F · `97zmdc6s`
- **fi** — Eero · M · `83c6f4fea98e` · Valtteri · M · `dfe7b9e7d217` · Elina · F · `34fd4dce1ba3` · Helmi · F · `c3a2c594479e`

## How to pick (per scenario)
1. **Language** — match the film's `language`. For a non-English film, prefer that language's native
   voice for the best accent (e.g. Chinese history → `Jian`/`Hao`); or use a multilingual voice and
   set `language` explicitly.
2. **Gender + energy to the topic** — documentary/authoritative → `leo`/`rex`; warm/inviting → `sal`/`ara`;
   bright/female lead → `eve` or native `Grace`.
3. Keep ONE voice for the whole film (consistency). Set it once in `voice.voice_id`.

Example: `"voice": {"voice_id": "grace", "language": "en", "speed": 1.0}` → wait, use the id:
`"voice": {"voice_id": "f8cf5c2c78d4", "language": "en", "speed": 1.0}` (Grace, native English female).

## Voice cloning (seed-audio)

To narrate in a real person's own voice, set `"voice": {"clone_ref": "path/to/sample.mp3",
"language": "en", "persona": "YouTube tutorial creator"}` — narration switches from xai/tts-v1
to `bytedance/seed-audio-1.0` with the sample pinned as @audio1 (template in `audio.py`;
timing validated beat-stable). A clean 20–60s solo-voice sample works best. `persona` tunes
delivery (e.g. "calm documentary narrator", "luxury brand voice-over").
