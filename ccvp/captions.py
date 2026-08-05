"""Optional burned-in captions.

Roughly 80% of feed video is watched muted, so captions are not a nicety. Two ways
to get them here, in increasing order of effort:

  srt_from_beats()  - free, instant, no dependencies. One caption per spoken beat,
                      timed from the marks the scene already recorded. Good enough
                      for most talking-points content.
  srt_from_whisper()- word-accurate timings via whisper.cpp (MIT). Use when you want
                      karaoke-style highlighting or the narration wanders off script.

Both write an .srt. `burn_in()` renders it into the picture, because platforms treat
uploaded caption files inconsistently and a burned-in caption always shows.
"""

import os
import shutil
import subprocess


def _ts(seconds):
    h, rem = divmod(max(0.0, seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{int(h):02d}:{int(m):02d}:{s:06.3f}".replace(".", ",")


def srt_from_beats(clips, marks, dest_srt, max_chars=42):
    """One caption per narration clip, split into readable lines."""
    import textwrap
    lines = []
    for i, (clip, start) in enumerate(zip(clips, marks), start=1):
        end = start + clip["duration"]
        body = "\n".join(textwrap.wrap(clip["text"], max_chars)[:3])
        lines.append(f"{i}\n{_ts(start)} --> {_ts(end)}\n{body}\n")
    os.makedirs(os.path.dirname(dest_srt) or ".", exist_ok=True)
    open(dest_srt, "w", encoding="utf-8").write("\n".join(lines))
    return dest_srt


def srt_from_whisper(wav, dest_srt, model="base.en", whisper_bin="whisper-cli"):
    """Word-accurate captions. Needs whisper.cpp built and a model downloaded.

    Falls back by raising - the caller should use srt_from_beats() instead.
    """
    exe = shutil.which(whisper_bin) or shutil.which("main")
    if not exe:
        raise RuntimeError(
            "whisper.cpp not found on PATH. Build it from "
            "https://github.com/ggerganov/whisper.cpp (MIT), or use srt_from_beats()")
    stem = os.path.splitext(dest_srt)[0]
    subprocess.run([exe, "-m", model, "-f", wav, "-osrt", "-of", stem], check=True)
    return dest_srt


def burn_in(video, srt, dest, font_size=20, margin_v=260):
    """Render captions into the picture. Sits above the platform's own UI furniture."""
    style = (f"FontSize={font_size},PrimaryColour=&H00FFFFFF,OutlineColour=&H99000000,"
             f"BorderStyle=3,Outline=2,Shadow=0,Alignment=2,MarginV={margin_v}")
    # ffmpeg's subtitles filter needs escaping on Windows paths.
    safe = srt.replace("\\", "/").replace(":", "\\:")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", video,
                    "-vf", f"subtitles='{safe}':force_style='{style}'",
                    "-c:v", "libx264", "-crf", "20", "-preset", "medium",
                    "-pix_fmt", "yuv420p", "-c:a", "copy",
                    "-movflags", "+faststart", dest], check=True)
    return dest
