"""Audio editing. ffmpeg underneath, so there is nothing extra to install.

    trim / concat / insert_silence          structure
    fade / normalise / limit / gain         level
    denoise / highpass / deess / warmth     repair and tone
    mix / duck / replace_audio / extract    combining
    speed / pitch                           timing
    detect_silence / strip_silence          cleanup
    waveform                                inspection

Bad audio loses a viewer faster than bad picture does. `voice_chain` runs the four
fixes that matter, in the order that actually works, and is what most raw narration
needs before it goes anywhere near a video.
"""

import json
import os
import re
import subprocess

TARGET_LUFS = -14.0     # what YouTube, Spotify and most feeds normalise to
VOICE_LUFS = -16.0      # a little lower for narration that sits under music


def _run(args):
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True)


def duration(src):
    return float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", src], capture_output=True, text=True, check=True).stdout.strip())


# ---- structure --------------------------------------------------------------
def trim(src, dest, start=0.0, end=None):
    args = ["-ss", str(start), "-i", src]
    if end is not None:
        args += ["-t", str(max(0.05, end - start))]
    _run(args + [dest])
    return dest


def concat(clips, dest):
    ins, parts = [], []
    for i, c in enumerate(clips):
        ins += ["-i", c]
        parts.append(f"[{i}:a]")
    _run([*ins, "-filter_complex",
          f"{''.join(parts)}concat=n={len(clips)}:v=0:a=1[a]", "-map", "[a]", dest])
    return dest


def insert_silence(src, dest, seconds=0.5, where="end"):
    pad = f"apad=pad_dur={seconds}" if where == "end" else f"adelay={int(seconds * 1000)}"
    _run(["-i", src, "-af", pad, dest])
    return dest


# ---- level ------------------------------------------------------------------
def fade(src, dest, fade_in=0.2, fade_out=0.4):
    d = duration(src)
    _run(["-i", src, "-af",
          f"afade=t=in:st=0:d={fade_in},afade=t=out:st={max(0, d - fade_out)}:d={fade_out}",
          dest])
    return dest


def normalise(src, dest, lufs=TARGET_LUFS):
    """Two-pass loudnorm. Delivering louder than the target just means the platform
    turns you down and you lose dynamic range for nothing."""
    probe = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", src, "-af",
         f"loudnorm=I={lufs}:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
        capture_output=True, text=True)
    match = re.search(r"\{[^{}]*input_i[^{}]*\}", probe.stderr, re.S)
    if match:
        m = json.loads(match.group(0))
        af = (f"loudnorm=I={lufs}:TP=-1.5:LRA=11:measured_I={m['input_i']}:"
              f"measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
              f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    else:
        af = f"loudnorm=I={lufs}:TP=-1.5:LRA=11"
    _run(["-i", src, "-af", af, dest])
    return dest


def gain(src, dest, db=3.0):
    _run(["-i", src, "-af", f"volume={db}dB", dest])
    return dest


def limit(src, dest, ceiling=0.95):
    _run(["-i", src, "-af", f"alimiter=limit={ceiling}", dest])
    return dest


# ---- repair and tone --------------------------------------------------------
def denoise(src, dest, floor_db=-30):
    """Kill hiss and room tone. `afftdn` needs no model and no extra install.

    `floor_db` is the assumed noise floor and ffmpeg only accepts -80..-20. Nearer -20
    is more aggressive (and starts to sound underwater); -30 is a safe default.
    """
    floor_db = max(-80, min(-20, floor_db))
    _run(["-i", src, "-af", f"afftdn=nf={floor_db}", dest])
    return dest


def highpass(src, dest, hz=80):
    """Roll off rumble, handling noise and desk thump. Almost always an improvement."""
    _run(["-i", src, "-af", f"highpass=f={hz}", dest])
    return dest


def deess(src, dest, hz=6500, reduction=-6):
    """Tame harsh S sounds, which cheap microphones exaggerate."""
    _run(["-i", src, "-af", f"equalizer=f={hz}:t=q:w=2:g={reduction}", dest])
    return dest


def warmth(src, dest, low_gain=2.0, presence=1.5):
    """A gentle broadcast curve: body at 200 Hz, intelligibility at 3 kHz."""
    _run(["-i", src, "-af",
          f"equalizer=f=200:t=q:w=1:g={low_gain},equalizer=f=3000:t=q:w=1:g={presence}",
          dest])
    return dest


def compress(src, dest, threshold=0.05, ratio=4):
    """Even out a performance that swings between whisper and shout."""
    _run(["-i", src, "-af",
          f"acompressor=threshold={threshold}:ratio={ratio}:attack=20:release=250", dest])
    return dest


def voice_chain(src, dest, lufs=VOICE_LUFS):
    """The four fixes raw narration nearly always needs, in the order that works:
    rumble out, noise down, dynamics evened, then loudness set last."""
    _run(["-i", src, "-af",
          f"highpass=f=80,afftdn=nf=-30,"
          f"acompressor=threshold=0.05:ratio=4:attack=20:release=250,"
          f"equalizer=f=3000:t=q:w=1:g=1.5,loudnorm=I={lufs}:TP=-1.5:LRA=11",
          dest])
    return dest


# ---- combining --------------------------------------------------------------
def mix(tracks, dest, gains=None):
    ins, parts, labels = [], [], []
    for i, t in enumerate(tracks):
        ins += ["-i", t]
        g = (gains or [1.0] * len(tracks))[i]
        parts.append(f"[{i}:a]volume={g}[m{i}]")
        labels.append(f"[m{i}]")
    parts.append(f"{''.join(labels)}amix=inputs={len(tracks)}:normalize=0[a]")
    _run([*ins, "-filter_complex", ";".join(parts), "-map", "[a]", dest])
    return dest


def duck(voice, music, dest, reduction=8, ratio=8):
    """Sidechain the music to the voice, so the bed drops only while someone speaks.
    Far better than a fixed low volume, which buries the music and still masks words."""
    _run(["-i", voice, "-i", music, "-filter_complex",
          f"[1:a][0:a]sidechaincompress=threshold=0.03:ratio={ratio}:"
          f"attack=20:release=350:makeup={reduction}[bed];"
          f"[0:a][bed]amix=inputs=2:normalize=0[a]",
          "-map", "[a]", dest])
    return dest


def extract(video, dest):
    _run(["-i", video, "-vn", "-acodec", "pcm_s16le", "-ar", "48000", dest])
    return dest


def replace_audio(video, audio, dest):
    _run(["-i", video, "-i", audio, "-map", "0:v", "-map", "1:a",
          "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest",
          "-movflags", "+faststart", dest])
    return dest


# ---- timing -----------------------------------------------------------------
def speed(src, dest, factor=1.1):
    """Tempo change without pitch shift. Chained because atempo caps at 2x per pass."""
    steps, remaining = [], factor
    while remaining > 2.0:
        steps.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        steps.append("atempo=0.5")
        remaining /= 0.5
    steps.append(f"atempo={remaining:.4f}")
    _run(["-i", src, "-af", ",".join(steps), dest])
    return dest


def pitch(src, dest, semitones=0):
    """Shift pitch, keeping length. Small negative values add authority to a thin voice."""
    factor = 2 ** (semitones / 12)
    _run(["-i", src, "-af",
          f"asetrate=48000*{factor:.6f},aresample=48000,atempo={1 / factor:.6f}", dest])
    return dest


# ---- cleanup ----------------------------------------------------------------
def detect_silence(src, noise_db=-35, min_len=0.6):
    """Silent ranges as [(start, end), ...]. Feed straight into an edit decision list."""
    out = subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", src, "-af",
         f"silencedetect=noise={noise_db}dB:d={min_len}", "-f", "null", "-"],
        capture_output=True, text=True).stderr
    starts = [float(m) for m in re.findall(r"silence_start: (-?[\d.]+)", out)]
    ends = [float(m) for m in re.findall(r"silence_end: (-?[\d.]+)", out)]
    return list(zip(starts, ends))


def strip_silence(src, dest, noise_db=-35, min_len=0.5):
    """Drop dead air. The single biggest improvement to unedited talking audio."""
    _run(["-i", src, "-af",
          f"silenceremove=start_periods=1:start_threshold={noise_db}dB:"
          f"start_silence={min_len}:stop_periods=-1:stop_threshold={noise_db}dB:"
          f"stop_silence={min_len}", dest])
    return dest


def waveform(src, dest, width=1600, height=400, colour="0x0a7d4d"):
    """Render the waveform as a PNG - handy for spotting clipping or a dead channel."""
    _run(["-i", src, "-filter_complex",
          f"showwavespic=s={width}x{height}:colors={colour}", "-frames:v", "1", dest])
    return dest
