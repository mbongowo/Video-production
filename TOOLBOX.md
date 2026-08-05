# The toolbox — every free and open tool, and where it fits

Status key: **built in** (ships and works out of the box) · **adapter** (a module here calls
it if you install it) · **companion** (run it separately; do not merge its code)

---

## Animation and composition

| Tool | Licence | Status | Notes |
|---|---|---|---|
| **Manim Community** | MIT | **built in** | The animation engine. `ccvp/templates.py` |
| **FFmpeg** | LGPL-2.1+ / GPL if built with x264 | **built in** | Mux, cover, format conversion. Install it; don't redistribute it |
| **Blender** (VSE + 3D) | GPL-2.0+ | companion | Scriptable in Python. Enormous capability; run it as its own app |
| **Kdenlive / Shotcut** | GPL | companion | GUI editors on the MLT framework, for hand-finishing |
| **LosslessCut** | GPL-2.0 | companion | Trim/merge without re-encoding — instant, no quality loss |
| **OpenShot / Olive** | GPL | companion | Simpler NLEs; Olive is good for burned-in styled text |
| **Subtitle Edit** | GPL | companion | The most complete subtitle tool: waveform, shot changes, format conversion |
| **MLT `melt`** | LGPL | companion | The scriptable CLI under Kdenlive/Shotcut |
| **Natron** | GPL-2.0 | companion | Node compositing, if you need After Effects-style work |
| **OpenMontage** | **AGPL-3.0** | companion | Agentic real-footage production. Genuinely powerful — but AGPL, so never merge it in. See LICENSING.md |
| **Remotion** | Source-available | — | Excluded: needs a paid company licence beyond 3 people |

## Voice

| Tool | Licence | Status | Notes |
|---|---|---|---|
| **Edge TTS** | GPL-3.0 tool / MS endpoint | **built in** (default) | ~400 voices, no key. Testing only — not for commercial use |
| **Kokoro-82M** | Apache-2.0 | adapter `kokoro` | **Best natural voice that is fully permissive.** `pip install kokoro soundfile` |
| **Chatterbox** | MIT | adapter `chatterbox` | **Cloning + emotion control.** The closest open equivalent to ElevenLabs |
| **F5-TTS** | MIT | adapter `clone` | Zero-shot cloning from ~15s of audio |
| **OpenVoice V2** | MIT | adapter `clone` | Cloning with tone/style control |
| **Piper** | MIT | adapter `piper` | Fastest, fully offline, tiny |
| **Dia** (Nari Labs) | Apache-2.0 | adapter `dia` | **Dialogue + non-verbals.** `[S1]`/`[S2]` turns, "(laughs)". Cleanest licence of the expressive models |
| **Orpheus** (Canopy) | Apache-2.0 code / **Llama 3.2 Community** weights | adapter `orpheus` | Very human prosody, emotion tags. Requires "Built with Llama" attribution |
| **StyleTTS2** | MIT | — | Very natural; add as an adapter if you want it |
| **Coqui XTTS-v2** | MPL code / **CPML weights** | — | Excluded: weights are non-commercial |
| **Fish Speech** | Open code / **non-commercial weights** | — | Excluded: needs a paid licence to sell output |
| **VibeVoice** | **Research only** | adapter (guarded) | Expressive and multi-speaker, but not licensed for commercial use |
| **ElevenLabs** | SaaS | — | Excluded: paid, and the free tier requires attribution |

## Captions and audio repair

| Tool | Licence | Status | Notes |
|---|---|---|---|
| **whisper.cpp** | MIT | adapter | Word-accurate timings. `ccvp/captions.py` |
| **faster-whisper** | MIT | adapter | Faster on GPU, same models |
| **Demucs** | MIT | adapter | Split speech from music. `ccvp/enhance.py` |
| **ffmpeg `loudnorm`** | — | **built in** | Normalise to -14 LUFS, what platforms target |

Captions are not optional in practice — most feed video is watched muted. The free path
(`srt_from_beats`) needs no extra install at all.

## Picture repair and polish — `ccvp/enhance.py`

| Tool | Licence | Notes |
|---|---|---|
| **auto-editor** | MIT/Unlicense | Cuts silence out of talking footage. Biggest single win on raw video |
| **rembg** | MIT | Background removal without a green screen |
| **Real-ESRGAN** | BSD-3 | 2–4x upscale for old or low-res footage |
| **RIFE** | MIT | Frame interpolation for smooth slow motion |

## Stock media and data — all free, none paid

| Source | Terms | Status |
|---|---|---|
| **Pexels** | Free, commercial use allowed | adapter `ccvp/stock.py` |
| **Pixabay** | Free, commercial use allowed | adapter `ccvp/stock.py` |
| **Unsplash** | Free, commercial use allowed | adapter `ccvp/stock.py` |
| **Wikimedia Commons** | PD / CC0 only (filtered) | adapter `ccvp/stock.py` — **needs no API key at all** |
| **Mixkit** | Free, no account, no attribution | companion — 4K b-roll, no API |
| **Videvo** | Free tier, per-clip terms | companion — video-first library |
| **Openverse** | CC-licensed search | companion — check each item's licence |
| **Natural Earth** | **Public domain** | **built in** — `ccvp/geo.py`. No attribution, no share-alike |
| **NASA imagery** | Public domain | companion — excellent for earth/space topics |
| **OpenStreetMap** | ODbL | — Not used: attribution + share-alike on derived databases |

Pexels and Pixabay need a free API key. There is no paid tier you can hit and no card to
enter. The animated templates need no imagery at all, which is also the only path with zero
third-party content risk.

## Local AI video generation — free if you have the GPU

From OpenMontage's zero-key path. All run offline with no per-second billing; all want a
capable NVIDIA GPU. Use them as **companions** that produce clips you then feed in.

| Model | Notes |
|---|---|
| **WAN 2.1** | 1.3B and 14B; the usual first choice for free local text-to-video |
| **LTX-Video** | Fast, good quality for its size |
| **HunyuanVideo** | High quality, heavy VRAM |
| **CogVideo** | 2B and 5B variants |

Check each model's own weights licence before commercial use — several AI video models ship
under OpenRAIL-style terms with use restrictions, which are *not* the same as MIT.

## Music

| Approach | Terms | Status |
|---|---|---|
| **Synthesised bed** (`ccvp/music.py`) | **Yours — generated from sine waves** | **built in** |
| **Stable Audio Open** | Stability Community Licence | companion | Free under a revenue threshold; attribution required |
| **MusicGen / AudioCraft** | MIT code / **CC-BY-NC weights** | — | **Excluded.** The MIT covers the library, not the music it makes |
| Free Music Archive / Musopen | Per-track, varies | companion |
| Epidemic / Artlist | Subscription | — Excluded: paid |

The synthesised bed is the reason there is no music subscription here. Nothing to license,
and no track for Content ID to match against.

## Fonts — check these, people forget

Manim uses whatever font you name. Many fonts bundled with an OS are licensed for viewing
documents, not for embedding in video you sell. Safe, permissive families: **Inter**,
**Roboto**, **Open Sans**, **Lato**, **Source Sans 3**, **DejaVu** — all SIL OFL or Apache.

---

## What ships versus what you add

Out of the box you get a complete, professional video with **only** Manim + ffmpeg + edge-tts.
Everything else in this table is a choice. The sensible upgrade path is:

1. `pip install kokoro soundfile` — the voice stops sounding synthetic
2. `pip install chatterbox-tts` — clone your own voice
3. A Pexels key — real footage when a topic needs it
4. `pip install auto-editor rembg` — if you start filming yourself
