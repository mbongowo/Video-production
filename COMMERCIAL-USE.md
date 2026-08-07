# Licensing — can I sell what this makes?

**Short answer: yes, on the default configuration.** This package is MIT. The videos it
produces are yours. But two of the tools in the wider toolbox would contaminate that, and
one common convenience has a catch — so read the table before you ship commercial work.

*I am not a lawyer and this is not legal advice. Licences change. Verify anything that
matters to your business, especially before signing a client contract.*

---

## The rule that makes this work

Your code **calls separate programs** (ffmpeg, piper, edge-tts) as subprocesses. It does not
link them into itself. Under the usual reading of the GPL family, running a separate
executable is *aggregation*, not derivation — so a GPL tool in your pipeline does not make
your pipeline GPL.

Two things follow, and both matter:

1. **Never bundle a copyleft binary into your distribution.** Require users to install
   ffmpeg themselves. The moment you ship their binary inside your zip, you are
   distributing their software and their terms attach to that copy.
2. **Never `import` a copyleft Python module.** Importing *is* linking. This is why
   `edge-tts` is invoked as `python -m edge_tts` in a subprocess and never imported.

---

## What ships in the default pipeline

| Tool | Licence | Sell the output? | Notes |
|---|---|---|---|
| **Your code (this package)** | MIT | ✅ | Do anything, keep the notice |
| **Manim Community Edition** | MIT | ✅ | The animation engine |
| **numpy** | BSD-3-Clause | ✅ | Synthesises the music bed |
| **Pillow** | MIT-CMU | ✅ | Cover checks |
| **FFmpeg** | LGPL-2.1+, or **GPL** if built with libx264/x265 | ✅ as a subprocess | Don't redistribute the binary. Encoder output is **not** a derivative work — your video is yours |
| **Piper TTS** | MIT | ✅ | **The commercially safest voice.** Fully offline |
| **whisper.cpp** *(optional captions)* | MIT | ✅ | Models are MIT too |

**The music bed is the quiet win.** It is synthesised from sine waves by `ccvp/music.py`, so
there is no catalogue to license and nothing for Content ID to match against. Most
"royalty-free" music still carries terms and still gets videos muted.

## The catch on the default voice

`edge-tts` is the default because it needs no key, no account and no install — which is
right for trying the tool out. For **commercial** work it has two problems:

1. **The package is GPL-3.0.** Fine as a subprocess, fatal if you ever `import` it.
2. **The endpoint is Microsoft's Edge "Read Aloud" service, used unofficially.** Microsoft
   does not offer it for arbitrary commercial use. This is a *terms of service* risk, not a
   copyright one, and no licence file will fix it.

**So: switch to Piper before you sell anything.** Set `"engine": "piper"` and point `voice`
at a `.onnx` model. It runs offline, it is MIT, and nobody's ToS is involved. Set
`"commercial": true` in your spec and the preflight check will fail the build if you left a
risky engine selected.

## The trap: "MIT" code with non-commercial weights

**An AI model has two licences, and the permissive one is usually the decoy.** The code is
MIT or Apache; the *weights* — the part that actually generates your audio or video — often
are not. Blog posts and even search results routinely quote the code licence and call the
model commercially safe. It is the single most common way people get this wrong.

| Model | Code | **Weights** | Sell the output? |
|---|---|---|---|
| **MusicGen / AudioCraft** | MIT | **CC-BY-NC 4.0** | ❌ Non-commercial. The MIT here covers the library, not the music |
| **Fish Speech** | Open | **Non-commercial** | ❌ Needs a paid licence for commercial use |
| **Coqui XTTS-v2** | MPL-2.0 | **CPML** | ❌ Non-commercial |
| **Stable Audio Open** | — | Stability Community | ⚠️ Free under a revenue threshold, attribution required |
| **Orpheus** | Apache-2.0 | **Llama 3.2 Community** | ⚠️ Fine for most, but requires "Built with Llama" attribution |
| **Kokoro-82M** | Apache-2.0 | Apache-2.0 | ✅ Clean |
| **Dia** | Apache-2.0 | Apache-2.0 | ✅ Clean |
| **Chatterbox** | MIT | MIT | ✅ Clean |
| **F5-TTS / OpenVoice V2** | MIT | MIT | ✅ Clean |

**This is why the music bed is synthesised rather than generated.** The obvious upgrade would
be to plug in MusicGen — but its weights are CC-BY-NC, so every video you sold with that
music would be infringing. Sine waves from `ccvp/music.py` are unglamorous and completely
yours. If you want AI-generated music commercially, Stable Audio Open is the nearest option,
and you still owe Stability attribution and must stay under their revenue threshold.

Before adding any model to this package, find its **weights** licence, not its repo licence.

## What is deliberately NOT in this package

Both are good tools. Neither can be part of something you sell without consequences.

| Tool | Licence | Why it is excluded |
|---|---|---|
| **OpenMontage** | **AGPL-3.0** | Strongest copyleft there is. Bundling or importing it forces your *entire* package to AGPL — and if you ever run it behind a web service, you must offer your full source to every user. Use it as a **separate application** on your own machine and the videos it makes are still yours. Just never merge its code into yours |
| **VibeVoice** | **Research only** | The authors do not licence it for commercial deployment. Expressive and multi-speaker, genuinely good — but not for paid client work |
| **Remotion** | Source-available | Free for individuals and companies up to 3 people; a paid company licence is required beyond that. Excluded so this package stays free for whoever you hand it to |
| **ElevenLabs** | SaaS terms | Free tier requires attribution and does not cover commercial use; needs a paid plan |

## Stock media, if you add it

`ccvp/stock.py` supports Pexels and Pixabay, both free and both allowing commercial use.
They are **content licences, not software licences**, and they have real conditions:
no reselling the raw asset, no implying endorsement, and care with identifiable people and
trademarks. Read the current terms for anything client-facing.

## Fonts — the trap people miss

Manim renders with whatever font you name. Plenty of fonts on a typical Windows machine are
licensed for *viewing documents*, not for embedding in video you sell. The default here uses
your system's standard sans stack. If you set a custom `font`, check that its licence permits
commercial use — this catches people out far more often than code licences do.

## A clean commercial setup

```jsonc
{
  "commercial": true,          // makes preflight enforce the rest
  "engine": "piper",           // MIT, offline, no ToS exposure
  "voice": "models/en_US-lessac-medium.onnx"
}
```

Plus: install ffmpeg yourself rather than shipping it, keep the synthesised music bed, and
use your own footage or properly-licensed stock. That configuration has no copyleft reaching
your code and no service terms reaching your output.
