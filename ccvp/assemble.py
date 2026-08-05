"""Mux picture + voice + music with ffmpeg, and cut the cover frame.

Narration clips are placed at the exact marks the scene recorded while rendering,
so nothing drifts even when a beat runs long. Music is looped under the whole
thing at a level that stays out of the way of speech.
"""

import json
import os
import subprocess

MUSIC_GAIN = 0.10       # bed level under narration
COVER_BRIGHT = 80       # peak luma above which a cover needs no lift


def _run(cmd):
    subprocess.run(cmd, check=True)


def peak_luma(path):
    """Brightest frame in the video, 0-255. The number that decides cover strategy."""
    p = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-vf",
         "fps=1,signalstats,metadata=print:file=-", "-f", "null", "-"],
        capture_output=True, text=True)
    vals = [float(l.split("=")[-1]) for l in p.stdout.splitlines() if "YAVG" in l]
    return max(vals) if vals else 0.0


def mux(silent_video, clips, marks, music_wav, dest, total=None):
    """Lay narration onto the silent render at `marks`, add the bed, write `dest`."""
    inputs = ["-i", silent_video]
    for c in clips:
        inputs += ["-i", c["file"]]
    inputs += ["-stream_loop", "-1", "-i", music_wav]

    music_idx = len(clips) + 1
    parts, labels = [], []
    for i, m in enumerate(marks[:len(clips)]):
        delay = int(round(m * 1000))
        parts.append(f"[{i + 1}:a]adelay={delay}|{delay},apad[a{i}]")
        labels.append(f"[a{i}]")

    dur = total or 0
    trim = f",atrim=0:{dur:.3f}" if dur else ""
    parts.append(f"[{music_idx}:a]volume={MUSIC_GAIN}{trim}[bed]")
    labels.append("[bed]")
    parts.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:"
                 f"dropout_transition=0[mixed]")
    # Keep the mix from clipping when a loud line lands on a swell.
    parts.append("[mixed]alimiter=limit=0.95[aout]")

    _run(["ffmpeg", "-y", "-v", "error", *inputs,
          "-filter_complex", ";".join(parts),
          "-map", "0:v", "-map", "[aout]",
          "-c:v", "libx264", "-crf", "20", "-preset", "medium",
          "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
          "-shortest", "-movflags", "+faststart", dest])
    return dest


def cover(video, dest_jpg, at_seconds, force_lift=None):
    """Cut a 1080x1920 cover. Lifts only a dark frame - lifting a bright one washes it out.

    Pick `at_seconds` where the hook is on screen: a cover carrying the hook beats a
    bare visual, and it is the same line the title should use.
    """
    lift = peak_luma(video) < COVER_BRIGHT if force_lift is None else force_lift
    vf = ("eq=brightness=0.14:contrast=1.35:saturation=1.30,scale=1080:1920"
          if lift else "scale=1080:1920")
    os.makedirs(os.path.dirname(dest_jpg) or ".", exist_ok=True)
    _run(["ffmpeg", "-y", "-v", "error", "-ss", f"{at_seconds}", "-i", video,
          "-frames:v", "1", "-update", "1", "-vf", vf, "-q:v", "2", dest_jpg])
    return dest_jpg


def load_timeline(path):
    t = json.load(open(path, encoding="utf-8"))
    return t["marks"], t["total"]
