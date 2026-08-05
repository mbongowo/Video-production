# Content Creation Video Pipeline

**Write a JSON file. Get a finished vertical video, a feed cover and a YouTube thumbnail.**

No subscription. No API key in the default setup. No per-character billing. Nothing in this
package has a paid tier you can hit, and nothing phones home with your script.

```bash
python make.py examples/morning_routine.json
```

```
[1/5] narration (edge)
[2/5] animation
[3/5] music bed
[4/5] mix and cover
[5/5] checks
  peak luma        226.7  ok
  ship checklist   passed

  video  out/morning_routine.mp4
  cover  out/morning_routine_cover.jpg      (1080x1920 reel/short tile)
  thumb  out/morning_routine_thumbnail.jpg  (1280x720 YouTube card)
```

---

## What you'd otherwise pay for

| What you want | The usual bill | Here |
|---|---|---|
| Natural narration | ElevenLabs, from $5/mo, metered per character | **Kokoro-82M** (Apache-2.0) or **Edge TTS**, unmetered |
| Voice cloning | ElevenLabs Creator, $22/mo | **Chatterbox** or **F5-TTS**, MIT, runs on your machine |
| Script → video | Pictory, from $19/mo | `python make.py spec.json` |
| Auto captions | Most editors charge for it | **whisper.cpp** (MIT), or free from the beat timings |
| Stock footage | Storyblocks, from $15/mo | **Pexels** + **Pixabay**, free forever |
| Music that won't get claimed | Epidemic Sound, $10/mo | **Synthesised here from sine waves** — no catalogue, nothing to Content ID |
| Thumbnails | Canva Pro, $12/mo | Generated for every video, automatically |

The music point is worth dwelling on: `ccvp/music.py` writes the bed from scratch with numpy.
There is no library to license and no track for a rights bot to match. Most "royalty-free"
music still carries terms and still gets videos muted.

## Install

```bash
python -m venv .venv && .venv/Scripts/activate     # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

You also need **ffmpeg** and **ffprobe** on your PATH — they are not pip packages:

- Windows `winget install Gyan.FFmpeg`
- macOS `brew install ffmpeg`
- Linux `sudo apt install ffmpeg`

That is the whole install. Everything else is optional.

## Write a video

A spec is a hook, some points, and an outro. The voice reads `say`; the screen shows
`label` and `note`, so on-screen text can stay tight while the narration reads naturally.

```json
{
  "id": "morning_routine",
  "format": "listicle",
  "title": "4 morning habits that actually stick",
  "hook": "Four morning habits that actually stick.",
  "accent": "#0a7d4d",
  "brand": "@yourhandle",
  "points": [
    { "label": "1. Same wake time", "note": "even on weekends",
      "say": "One. Wake up at the same time, even on weekends." }
  ],
  "outro": "Pick one. Give it a week.",
  "cta": "Follow for more",
  "caption": "...",
  "hashtags": ["#habits", "#productivity", "#discipline", "#selfimprovement"]
}
```

### Formats

| `format` | Shape | Good for |
|---|---|---|
| `listicle` | Numbered points revealed one at a time | tips, lists, "5 things" |
| `howto` | Steps with a progress bar | tutorials, processes |
| `myth` | Alternating claim / correction panels | myth-busting, misconceptions |
| `quote` | Large statements with an accent rule | opinions, stories, hot takes |
| `map` | **Real country borders and real projections** | geography, travel, data, news |

## Voices

Set `"engine"` in the spec. All free, none metered.

| Engine | What it is | Licence | Notes |
|---|---|---|---|
| `edge` *(default)* | ~400 Microsoft neural voices | GPL-3.0 tool, MS endpoint | No key. **Not for commercial use** — see LICENSING.md |
| `kokoro` | Kokoro-82M | Apache-2.0 | **Most natural fully-permissive model.** `pip install kokoro soundfile` |
| `chatterbox` | Resemble AI Chatterbox | MIT | **Cloning + emotion control.** Closest open thing to ElevenLabs |
| `clone` | F5-TTS or OpenVoice V2 | MIT | Zero-shot clone from ~15s of reference audio |
| `piper` | Offline neural TTS | MIT | Fastest, no network at all |
| `vibevoice` | Expressive, multi-speaker | **Research only** | Not licensed for commercial work |

### Voice cloning

```jsonc
{ "engine": "chatterbox", "voice": "assets/my_voice.wav" }
```

Record 15–30 seconds of clean speech, point `voice` at it, done. It runs locally — your
voice is never uploaded and there is no per-character charge. A GPU makes it seconds per
line rather than minutes.

**Only clone a voice you own or have written permission to use.**

## Selling what you make

Yes — on the right configuration. The package is MIT and the videos are yours. Two tools in
the wider ecosystem would contaminate that and are deliberately excluded.

```jsonc
{
  "commercial": true,       // preflight now fails the build on a risky engine
  "engine": "kokoro"        // or piper / chatterbox / clone
}
```

**Read [LICENSING.md](LICENSING.md).** It covers why `edge` is fine for testing but not for
selling, why OpenMontage (AGPL-3.0) and VibeVoice (research-only) are excluded, and the font
trap that catches more people than any code licence.

## Optional extras

Everything below is free and open. Install only what you want — see [TOOLBOX.md](TOOLBOX.md).

- **Captions** — `ccvp/captions.py`, free from beat timings or word-accurate via whisper.cpp
- **Stock media** — `ccvp/stock.py`, Pexels and Pixabay (free keys, no payment ever)
- **Polish** — `ccvp/enhance.py`: silence trimming, background removal, upscaling, frame
  interpolation, loudness normalisation, and 1:1 / 16:9 versions from the same master

## Why the checks exist

Every automated check here corresponds to a fault that shipped in a real, published video:

- **Peak luma.** A dark render gives the platform nothing but a black tile to auto-pick as
  your cover. Instagram and TikTok covers are set at upload and are **permanent**.
- **Edge clipping** (`--deep`). Labels running off the side of the frame. Reviewing four
  videos by eye missed two; this found both in one pass.
- **Ship checklist.** Empty captions and filenames used as titles. On one real account, the
  single Short with a proper title and description got 102 views; three shipped without got
  5, 16 and 26. Same audience, same week.

## Licence

MIT — see [LICENSE](LICENSE). Third-party tools carry their own terms; [LICENSING.md](LICENSING.md)
breaks them down per tool with a commercial verdict for each.
