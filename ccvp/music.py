"""A calm ambient bed, synthesised from scratch - so there is nothing to license.

Every "royalty-free" music site still attaches terms, and platforms will happily
mute a video over a bad match. These are plain sine pads written by numpy: you
own the output, and it cannot be content-ID'd against anyone else's catalogue.

Two voicings sharing tones cross-fade, so it loops without a seam.
"""

import os
import wave

import numpy as np

SR = 44100

MOODS = {
    # (chord A, chord B) - both share notes so the crossfade is smooth.
    "calm": ([130.81, 196.00, 261.63, 329.63], [110.00, 164.81, 220.00, 329.63]),
    "uplifting": ([146.83, 220.00, 293.66, 369.99], [123.47, 185.00, 246.94, 369.99]),
    "focus": ([110.00, 164.81, 220.00, 277.18], [98.00, 146.83, 196.00, 277.18]),
    "warm": ([116.54, 174.61, 233.08, 293.66], [103.83, 155.56, 207.65, 293.66]),
}


def _pad(t, freqs):
    out = np.zeros_like(t)
    for i, f in enumerate(freqs):
        # A slow detune per voice keeps it from sounding like a test tone.
        vib = 1.0 + 0.0022 * np.sin(2 * np.pi * (0.18 + 0.05 * i) * t)
        out += np.sin(2 * np.pi * f * vib * t) / (i + 1.6)
    return out


def bed(dest_wav, seconds=32.0, mood="calm"):
    """Write a loopable ambient bed. Returns the path."""
    chord_a, chord_b = MOODS.get(mood, MOODS["calm"])
    t = np.linspace(0, seconds, int(SR * seconds), endpoint=False)

    # Cross-fade A <-> B twice over the loop, starting and ending on A.
    blend = 0.5 - 0.5 * np.cos(2 * np.pi * t / seconds * 2)
    sig = _pad(t, chord_a) * (1 - blend) + _pad(t, chord_b) * blend

    # A breath of air on top, and a gentle low-pass so it never competes with speech.
    sig += 0.015 * np.sin(2 * np.pi * 1180 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.07 * t))
    kernel = np.ones(64) / 64
    sig = np.convolve(sig, kernel, mode="same")

    # Ease the very start and end so a loop point is inaudible.
    edge = int(SR * 0.75)
    ramp = np.linspace(0, 1, edge)
    sig[:edge] *= ramp
    sig[-edge:] *= ramp[::-1]

    peak = np.max(np.abs(sig)) or 1.0
    pcm = np.int16(sig / peak * 32767 * 0.5)

    os.makedirs(os.path.dirname(dest_wav) or ".", exist_ok=True)
    with wave.open(dest_wav, "w") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    return dest_wav
