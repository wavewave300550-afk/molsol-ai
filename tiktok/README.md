# Science TikTok production system

Reusable pipeline for Thai science TikTok episodes, built with
[Remotion](https://www.remotion.dev), FFmpeg and ElevenLabs.

```
episode.json ─► validate ─► approve ─► narration ─► timeline ─► render ─► verify ─► MP4
 (Thai script,   (rules)    (human     (ElevenLabs   (scenes,     (1080×1920, (codec, size,
  visuals,                   review)    Thai voice,   cues and     30 fps,     fps, length,
  sources)                              or a file)    subtitles    H.264)      sync, decode)
                                                      follow the
                                                      voice)
```

The narration is the clock. The video lasts as long as the narration plus a
0.8 s tail, each scene cuts in just before its first spoken word, animations
fire on the words they illustrate, and the Thai subtitles follow the voice
word by word. Nothing ever speeds up, compresses or cuts the narration to fit a
length: if it is too long, the script is changed.

## Quick start

Needs Node.js 22.18 or newer. FFmpeg ships with Remotion; nothing else to install.

```bash
cd tiktok
npm ci
npm run pipeline:test     # full test render, no ElevenLabs key needed
```

`pipeline:test` makes temporary test audio (tones timed like speech, not a
voice), imports it like a recording, renders `episodes/pipeline-test`, and
verifies `out/pipeline-test.mp4`. Test renders carry a red TEST badge and
must never be published.

## Making an episode

1. **Start a script:** `npm run new-episode -- ep001-water "ชื่อตอน"`
   creates `episodes/ep001-water/episode.json` from the template.
2. **Write it:** scenes with Thai narration, a visual for each scene, cue
   words, and the sources behind every claim (format below).
3. **Check it:** `npm run validate -- ep001-water`
4. **Review and approve it.** A person checks every claim against its
   source, adds `"accessed": "YYYY-MM-DD"` to each source they opened, then:
   `npm run approve -- ep001-water --by "Reviewer name"`. Commit the file.
5. **Narrate it:** `npm run narrate -- ep001-water` (ElevenLabs, see below).
   A human recording works too:
   `npm run audio:import -- ep001-water path/to/recording.m4a`
6. **Render it:** `npm run render -- ep001-water` writes
   `out/ep001-water.mp4`, `out/ep001-water.description.txt` (title and
   sources for the TikTok description) and `out/ep001-water.report.json`.
   Or run it on GitHub and download it on your phone (see below).

Commit `public/episodes/<id>/narration.source.mp3`, `alignment.json` and
`narration.json` after narrating, so later renders reuse the same take
instead of paying for a new one.

## Rules the system enforces

| Rule | Where |
| --- | --- |
| Standard episodes 60–90 s; complex episodes up to 120 s only with `"durationTier": "complex"`, a `complexJustification` and approval | `validate` (estimate), `narrate` and `timeline` (real length) |
| The narration's real length decides the video; it is never sped up, compressed or cut | `timeline`, `calculateMetadata`, `verify` |
| No profanity in narration or on screen (Thai matched word by word, so หีบ or กูเกิล pass) | `validate` |
| No sentence-final ครับ, ค่ะ or คะ in the narration | `validate` |
| Every factual scene cites a source; every source has a URL or DOI; a sources card ends the video | `validate` |
| Narration only for an approved script; any edit after approval voids it | `approve`, `narrate`, `timeline` |
| 1080×1920, 30 fps, H.264 + AAC, `yuv420p`, index at the front (iPhone) | `render`, `verify` |

Warnings (like a source nobody has checked yet) do not block, but the
reviewer accepts them when approving.

## The script: `episodes/<id>/episode.json`

Editors that read `"$schema"` autocomplete it (`episodes/episode.schema.json`,
regenerate with `npm run schema`). The test episode is a complete example.

```jsonc
{
  "id": "ep001-water", "kind": "episode", "title": "…", "language": "th",
  "durationTier": "standard",            // or "complex" + "complexJustification"
  "glossary": ["ไมโทคอนเดรีย"],          // optional: words subtitles must not split
  "sources": [{ "id": "pubchem-water", "label": "PubChem: Water",
                "citation": "…", "url": "https://…", "accessed": "2026-11-20" }],
  "scenes": [{
    "id": "molecule", "label": "โมเลกุลของน้ำ",
    "narration": "น้ำหนึ่งโมเลกุลประกอบด้วยไฮโดรเจนสองอะตอม และออกซิเจนหนึ่งอะตอม",
    "sourceIds": ["pubchem-water"],
    "cues": [{ "id": "hydrogen", "text": "ไฮโดรเจน" }],
    "visual": { "type": "molecule", "reveal": { "hydrogen": ["H1", "H2"] }, … }
  }],
  "approval": null                       // written by npm run approve
}
```

Narration is spoken and shown as subtitles word for word, so write numbers
the way they should be read. Use spaces between phrases as Thai does; they
become pauses and subtitle breaks. Set `"factual": false` on scenes that make
no scientific claim (intro, outro).

| Visual `type` | Shows | Cues |
| --- | --- | --- |
| `title` | title, kicker, subtitle, animated atom | – |
| `molecule` | atoms and bonds from 2D coordinates, formula with subscripts | `reveal`: cue → atom ids appear when spoken |
| `chart` | up to 6 bars, negative values hang below zero | `bars[].cue`: bar grows when spoken |
| `process` | 2–6 steps that light up in turn | `steps[].cue` |
| `fact` | 1–4 numbers that count up | `items[].cue` |
| `image` | an illustration from `public/` with its credit | – |
| `sources` | the end card listing every source | – |

## ElevenLabs narration (Thai)

- Model `eleven_v4` with `language_code: "th"`, called through the
  `/with-timestamps` endpoint so every character's timing comes back with the
  audio. There is no speed setting anywhere: the voice keeps its natural pace.
- The key is only read from `ELEVENLABS_API_KEY` and never logged or written:
  - **GitHub Actions:** repository secret `ELEVENLABS_API_KEY`.
  - **This computer:** `tiktok/.env` (git-ignored; see `.env.example`).
  - **Claude Code cloud session:** save it as an environment secret for
    `api.elevenlabs.io` (header `xi-api-key`); the proxy adds it to each
    request. Run with `ELEVENLABS_API_KEY=injected-by-proxy` and
    `NODE_USE_ENV_PROXY=1` (Node's `fetch` only uses the proxy with it).
- **Narrator:** every episode is read by the channel's permanent Thai voice,
  **Madame Scientia** (`XAF1635HwW2TJGfbLzfc`, set in `src/lib/config.ts`).
  A take only uses another voice when one is given explicitly (`--voice <id>`,
  the `ELEVENLABS_VOICE_ID` variable, or `voice.voiceId` in an episode), and
  the narration step says so. The pipeline never creates or edits voices.
- **Check before spending credits:** `npm run narrate -- <id> --dry-run`
  shows the voice, model, request URL and character count without sending
  anything. **Actions → ElevenLabs check → Run workflow** confirms the GitHub
  secret is set, the key works and it can use Madame Scientia, using
  read-only requests only (no audio, no credits).
- The same script, voice and model is never narrated twice (`--force` makes a
  new take). After mastering, the narration plays at -14 LUFS.

## Rendering on GitHub and downloading on iPhone

Workflow: `.github/workflows/tiktok-render.yml`.

- **Pull requests** that touch `tiktok/` run lint, tests and the full test render.
- **Manual run:** on github.com (Safari works), open **Actions → TikTok
  render → Run workflow**, enter the episode id, pick the narration
  (`auto` reuses a committed take when it matches the script, else calls
  ElevenLabs) and keep **publish** ticked. Manual runs are only available once
  the workflow is on the default branch (`main`).
- **Download:** the run summary links the MP4 on the **TikTok renders**
  pre-release (`…/releases/tag/tiktok-renders`). On iPhone, tap the link, play
  it, then Share → Save Video. Every run also keeps a zip artifact for 30 days,
  with the description, the verification report and any new ElevenLabs take
  (commit that take to reuse it).

## How timing works

1. `narration.wav`: the narration, mastered by FFmpeg with one constant gain
   and resampled to 48 kHz. The step fails if the length changes by more
   than 10 ms.
2. `alignment.json`: the start and end time of every character, from
   ElevenLabs. For a recording, it is estimated from the pauses with FFmpeg
   (`silencedetect`, adaptive threshold): accurate to the phrase, close for
   single words.
3. `timeline.json` (`npm run timeline`): scene frames, cue frames and subtitle
   pages, with video length = narration + 0.8 s. Thai words come from
   `Intl.Segmenter`. Science loanwords the dictionary splits (ไมโทคอนเดรีย)
   are kept whole using `src/lib/glossary.ts` and the episode `glossary`.
4. Remotion's `calculateMetadata` re-measures `narration.wav` and refuses to
   render if it no longer matches the timeline.

## Commands

| Command | Does |
| --- | --- |
| `npm run new-episode -- <id> ["title"]` | new script from the template |
| `npm run validate -- <id>` | check the script |
| `npm run approve -- <id> --by "Name"` | record the scientific review |
| `npm run voices` | list ElevenLabs voices, narrator marked (needs the key) |
| `npm run elevenlabs:check [-- --online]` | is the key set, which voice, does the key work (no credits) |
| `npm run narrate -- <id> --dry-run` | show exactly what narration would send, without sending |
| `npm run narrate -- <id>` | Thai narration with ElevenLabs (Madame Scientia) |
| `npm run audio:import -- <id> <file> [--test]` | use a recording (or test audio) as narration |
| `npm run narration:prepare -- <id>` | rebuild `narration.wav` from a committed take |
| `npm run audio:test -- <id>` | write temporary test audio for a script |
| `npm run timeline -- <id>` | build the timeline only |
| `npm run render -- <id>` | render and verify the MP4 |
| `npm run verify -- <id>` | verify an existing MP4 |
| `npm run pipeline:test` | everything above with test audio, no key |
| `npm run dev` | Remotion Studio preview |
| `npm run check` | lint, type-check, unit tests |

## Remotion Studio

`npm run dev` opens the preview. Scenes, subtitles and cues are generated
from the script and the narration timing, so their timing is not dragged
around in Studio: edit `episode.json`, re-narrate, and the video follows.
Run `npm run render` (or `npm run timeline`) once first so the episode has a
timeline.

## Project layout

```
episodes/<id>/episode.json   the script (source of truth, reviewed and approved)
public/episodes/<id>/        narration and timing for that episode
public/fonts/                Kanit and Noto Sans Thai (SIL OFL), no font CDN needed
public/illustrations/        images used by "image" scenes
src/lib/                     shared logic: schema, rules, timing, subtitles (Node + browser)
src/scenes/, src/components/ the Remotion video
scripts/                     the commands above
tests/                       unit tests (node --test)
```

## Licences

- Remotion is free for individuals and companies of up to 3 people; larger
  companies need a [company license](https://www.remotion.dev/docs/license).
  Put its key in the `REMOTION_LICENSE_KEY` secret and renders pass it on.
- Fonts: SIL Open Font License (`public/fonts/*-OFL.txt`).
- Credit every illustration in its scene (`credit`) and use only images you
  may publish.
