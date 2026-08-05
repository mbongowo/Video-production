"""Narration, with four interchangeable engines. All free, none metered.

    edge       (default)  Microsoft Edge neural TTS. ~400 voices in many languages
                          and accents. No key, no account, no cost. Needs net.
    piper      (optional)  Fully offline neural TTS. MIT, no network, no key - the
                          safe pick for commercial work on a laptop.
    kokoro     (optional)  Kokoro-82M, Apache-2.0. The most natural-sounding fully
                          permissive model - small, fast, beats far larger ones.
    chatterbox (optional)  Resemble AI Chatterbox, MIT. Zero-shot cloning WITH
                          emotion control - it beat ElevenLabs in blind tests.
    dia        (optional)  Nari Labs Dia, Apache-2.0. Dialogue and non-verbals
                          ([S1]/[S2] turns, "(laughs)") - best for two-handers.
    orpheus    (optional)  Canopy Labs Orpheus. Very human prosody, but inherits
                          the Llama 3.2 Community Licence - attribution required.
    clone      (optional)  Zero-shot VOICE CLONING from ~15 seconds of reference
                          audio, via F5-TTS or OpenVoice V2. Both MIT, both local.
    vibevoice  (optional)  Expressive, multi-speaker, long-form. RESEARCH ONLY - its
                          authors do not licence it for commercial deployment.

There is no paid tier anywhere in this file, and no engine here bills per character.

Whatever the engine, the output contract is the same: one 16 kHz mono WAV per
spoken beat plus its measured duration, which is what lets the animation hold each
beat exactly as long as the voice needs.
"""

import json
import os
import shutil
import subprocess
import sys

# A few Edge voices worth knowing. `python -m edge_tts --list-voices` lists them all -
# pick one that sounds like the audience you are talking to.
VOICES = {
    "warm-us-male": "en-US-AndrewNeural",
    "clear-us-male": "en-US-BrianNeural",
    "bright-us-female": "en-US-AvaNeural",
    "calm-us-female": "en-US-EmmaNeural",
    "uk-female": "en-GB-SoniaNeural",
    "uk-male": "en-GB-RyanNeural",
    "nigerian-female": "en-NG-EzinneNeural",
    "nigerian-male": "en-NG-AbeoNeural",
    "indian-female": "en-IN-NeerjaNeural",
    "australian-female": "en-AU-NatashaNeural",
}
DEFAULT_VOICE = "en-US-AndrewNeural"


def resolve_voice(name):
    """Accept either a friendly key from VOICES or a raw Edge voice id."""
    return VOICES.get(name, name) if name else DEFAULT_VOICE


def duration(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path],
        capture_output=True, text=True, check=True).stdout.strip()
    return float(out)


def _which(name):
    """Find an executable, including one installed into the *running* venv.

    `shutil.which` only searches PATH. When someone runs `venv/Scripts/python make.py`
    without activating the venv - which is completely normal - PATH does not contain
    the venv's Scripts/bin, so a pip-installed piper.exe sitting right next to the
    interpreter is invisible. Look there too.
    """
    found = shutil.which(name)
    if found:
        return found
    here = os.path.dirname(sys.executable)
    for candidate in (os.path.join(here, name), os.path.join(here, name + ".exe")):
        if os.path.exists(candidate):
            return candidate
    return None


def _to_wav(src, dest_wav):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src,
                    "-ar", "16000", "-ac", "1", dest_wav], check=True)


# ---- engines ----------------------------------------------------------------
def _edge(text, dest_wav, voice, rate):
    tmp = dest_wav + ".mp3"
    subprocess.run([sys.executable, "-m", "edge_tts", "--voice", resolve_voice(voice),
                    "--rate", rate, "--text", text, "--write-media", tmp],
                   check=True, capture_output=True)
    _to_wav(tmp, dest_wav)
    os.remove(tmp)


def _piper(text, dest_wav, voice, rate):
    """Offline. `voice` is a path to a .onnx model - see PIPER setup in the README."""
    exe = _which("piper")
    if not exe:
        raise RuntimeError("piper is not on PATH - install it or use engine 'edge'")
    if not voice or not os.path.exists(voice):
        raise RuntimeError("piper needs `voice` set to a .onnx model path")
    tmp = dest_wav + ".raw.wav"
    subprocess.run([exe, "--model", voice, "--output_file", tmp],
                   input=text.encode("utf-8"), check=True)
    _to_wav(tmp, dest_wav)
    os.remove(tmp)


def _kokoro(text, dest_wav, voice, rate):
    """Kokoro-82M (Apache-2.0). Small, fast, and the most natural-sounding of the
    fully-permissive models - it consistently beats far larger ones in blind tests.

    `pip install kokoro soundfile`. Runs on CPU at roughly real time; no key, no net
    after the one-time model download. `voice` is a preset id like "af_heart".
    """
    import soundfile as sf  # noqa: PLC0415 - optional backend
    from kokoro import KPipeline  # noqa: PLC0415

    pipe = _kokoro.__dict__.setdefault("_p", KPipeline(lang_code="a"))
    chunks = [audio for _, _, audio in pipe(text, voice=voice or "af_heart")]
    if not chunks:
        raise RuntimeError("kokoro returned no audio")
    import numpy as np  # noqa: PLC0415
    sf.write(dest_wav, np.concatenate(chunks), 24000)
    _to_wav(dest_wav, dest_wav)  # normalise to 16 kHz mono like the other engines


def _chatterbox(text, dest_wav, voice, rate):
    """Chatterbox (Resemble AI, MIT). Zero-shot cloning WITH emotion control - the
    closest open equivalent to what ElevenLabs sells, and the least robotic option
    here. `pip install chatterbox-tts`. Wants a GPU; works on CPU, slowly.

    `voice` is a reference .wav to clone; omit it for the stock voice.
    """
    import torchaudio  # noqa: PLC0415 - optional backend
    from chatterbox.tts import ChatterboxTTS  # noqa: PLC0415

    model = _chatterbox.__dict__.get("_m")
    if model is None:
        import torch  # noqa: PLC0415
        device = "cuda" if torch.cuda.is_available() else "cpu"
        model = _chatterbox.__dict__["_m"] = ChatterboxTTS.from_pretrained(device=device)
    wav = model.generate(text, audio_prompt_path=voice) if voice else model.generate(text)
    torchaudio.save(dest_wav, wav, model.sr)
    _to_wav(dest_wav, dest_wav)


def _dia(text, dest_wav, voice, rate):
    """Dia by Nari Labs (Apache-2.0, cleanly). Dialogue-first: it renders [S1]/[S2]
    turns and non-verbals like (laughs) or (sighs), which is what makes a two-hander
    or a reaction beat stop sounding like one person reading a list.

    `pip install nari-tts`. Wants a GPU. Write turns straight into the text:
        "[S1] Wait, you did what? [S2] I know. (laughs) It worked."
    """
    import soundfile as sf  # noqa: PLC0415 - optional backend
    from dia.model import Dia  # noqa: PLC0415

    model = _dia.__dict__.get("_m")
    if model is None:
        model = _dia.__dict__["_m"] = Dia.from_pretrained("nari-labs/Dia-1.6B")
    sf.write(dest_wav, model.generate(text), 44100)
    _to_wav(dest_wav, dest_wav)


def _orpheus(text, dest_wav, voice, rate):
    """Orpheus by Canopy Labs. Very human prosody, with emotion tags like <laugh>.

    LICENCE CARE: the code is Apache-2.0 but the model is built on a Llama 3.2
    backbone, so it inherits the **Llama 3.2 Community License** - which requires a
    "Built with Llama" attribution and carries a large-scale-user clause. That is
    permissive enough for most people but it is NOT plain Apache-2.0. If you want
    zero attribution obligations, use kokoro or dia instead.

    `pip install orpheus-speech`. `voice` is a preset like "tara".
    """
    import soundfile as sf  # noqa: PLC0415 - optional backend
    from orpheus_tts import OrpheusModel  # noqa: PLC0415

    model = _orpheus.__dict__.get("_m")
    if model is None:
        model = _orpheus.__dict__["_m"] = OrpheusModel(
            model_name="canopylabs/orpheus-tts-0.1-finetune-prod")
    chunks = list(model.generate_speech(prompt=text, voice=voice or "tara"))
    if not chunks:
        raise RuntimeError("orpheus returned no audio")
    import numpy as np  # noqa: PLC0415
    sf.write(dest_wav, np.concatenate(chunks), 24000)
    _to_wav(dest_wav, dest_wav)


def _clone(text, dest_wav, voice, rate):
    """Zero-shot voice cloning from a short reference recording. Free, local, MIT.

    `voice` is a path to a WAV of the voice to clone - 10-30 seconds of clean speech
    is plenty. Nothing is uploaded and there is no per-character cost.

    Backends, tried in order. Both are MIT, so cloned output is safe to sell:
      F5-TTS     pip install f5-tts        (https://github.com/SWivid/F5-TTS)
      OpenVoice  MyShell OpenVoice V2      (https://github.com/myshell-ai/OpenVoice)

    Runs on CPU but wants a GPU: expect a few seconds per line with one, a few
    minutes without. Deliberately NOT Coqui XTTS, whose model licence forbids
    commercial use - see LICENSING.md.

    Only clone a voice you own or have explicit permission to use.
    """
    if not voice or not os.path.exists(voice):
        raise RuntimeError("engine 'clone' needs `voice` set to a reference .wav path")

    try:
        from f5_tts.api import F5TTS  # noqa: PLC0415 - optional backend
    except ImportError:
        pass
    else:
        model = _clone.__dict__.setdefault("_f5", F5TTS())
        model.infer(ref_file=voice, ref_text="", gen_text=text, file_wave=dest_wav)
        return

    try:
        import openvoice_cli  # noqa: F401,PLC0415 - optional backend
    except ImportError as e:
        raise RuntimeError(
            "no cloning backend installed. `pip install f5-tts` (MIT), or install "
            "OpenVoice V2. Both are free and run locally - see README > Voice cloning"
        ) from e
    subprocess.run([sys.executable, "-m", "openvoice_cli", "single",
                    "-i", text, "-r", voice, "-o", dest_wav], check=True)


def _vibevoice(text, dest_wav, voice, rate):
    """Optional expressive engine. RESEARCH ONLY - see the licence note above.

    Expects a `vibevoice_tts` module exposing synth(text, dest, voice=...), which is
    how the original pipeline wired it. Any failure should fall back to edge.
    """
    import vibevoice_tts as vv  # noqa: PLC0415 - optional, imported only when chosen
    vv.synth(text, dest_wav, voice=voice)
    if not os.path.exists(dest_wav):
        raise RuntimeError("vibevoice produced no file")


ENGINES = {"edge": _edge, "piper": _piper, "kokoro": _kokoro, "dia": _dia,
           "orpheus": _orpheus, "chatterbox": _chatterbox, "clone": _clone,
           "vibevoice": _vibevoice}


def say(text, dest_wav, voice=None, rate="-5%", engine="edge", allow_fallback=True):
    """Synthesise one line to 16 kHz mono WAV. Returns its duration in seconds.

    `allow_fallback=False` makes a missing engine an error instead of quietly
    substituting edge. build.py sets it whenever the spec declares commercial use -
    silently swapping in edge there would hand you a licence problem while the
    preflight check, which only sees the *declared* engine, still reported a pass.
    """
    os.makedirs(os.path.dirname(dest_wav), exist_ok=True)
    fn = ENGINES.get(engine)
    if fn is None:
        raise SystemExit(f"unknown voice engine {engine!r} - pick one of {sorted(ENGINES)}")
    try:
        fn(text, dest_wav, voice, rate)
    except Exception as e:
        # Never silently swap a cloned voice for a stock one, and never downgrade a
        # deliberately licence-safe engine to one that is not.
        if engine in ("edge", "clone", "chatterbox") or not allow_fallback:
            raise
        print(f"    ({engine} unavailable -> falling back to edge: {e})")
        _edge(text, dest_wav, None, rate)
    return duration(dest_wav)


def narrate(lines, out_dir, voice=None, rate="-5%", engine="edge", allow_fallback=True):
    """Voice every beat. Returns [{index, text, file, duration}, ...].

    Cached against the exact inputs, because TTS is the slowest step here and you
    will re-render the picture far more often than you rewrite the script.
    """
    os.makedirs(out_dir, exist_ok=True)
    manifest = os.path.join(out_dir, "narration.json")
    signature = {"engine": engine, "voice": voice, "rate": rate, "lines": lines}

    if os.path.exists(manifest):
        try:
            cached = json.load(open(manifest, encoding="utf-8"))
            if cached.get("signature") == signature and all(
                    os.path.exists(c["file"]) for c in cached["clips"]):
                print("  narration unchanged - reusing cached clips")
                return cached["clips"]
        except (ValueError, KeyError):
            pass

    clips = []
    for i, text in enumerate(lines):
        dest = os.path.join(out_dir, f"{i:02d}.wav")
        preview = text if len(text) <= 56 else text[:56] + "..."
        print(f"  voicing {i + 1}/{len(lines)}: {preview}")
        clips.append({"index": i, "text": text, "file": dest,
                      "duration": round(say(text, dest, voice, rate, engine,
                                           allow_fallback), 3)})

    json.dump({"signature": signature, "clips": clips},
              open(manifest, "w", encoding="utf-8"), indent=1)
    return clips
