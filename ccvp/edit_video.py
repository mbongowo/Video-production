"""Video editing. Everything here is ffmpeg underneath - no editor, no timeline, no GUI.

These are the operations you actually reach for when finishing social video:

    trim / cut_out / concat / crossfade      structure
    speed / reverse / loop / freeze_frame    timing
    overlay / picture_in_picture / watermark compositing
    chroma_key / crop_aspect / rotate / flip framing
    grade / fade / vignette                  look
    burn_text / progress_bar                 furniture
    to_gif / extract_frames / contact_sheet  export

Every function takes paths and returns the destination path, so they chain:

    grade(trim(src, "a.mp4", 2, 14), "b.mp4", contrast=1.1)

Re-encodes by default because stream-copy only cuts on keyframes and silently
gives you the wrong in-point. `fast=True` opts into copy where it is safe.
"""

import json
import os
import subprocess

# Windows ships no fontconfig, so ffmpeg's drawtext cannot resolve a font by name -
# it needs an explicit file. Same list the thumbnail composer uses.
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\seguibl.ttf", r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]


def _default_font():
    return next((p for p in FONT_CANDIDATES if os.path.exists(p)), None)


CRF = "20"
PRESET = "medium"


def _run(args):
    subprocess.run(["ffmpeg", "-y", "-v", "error", *args], check=True)


def _enc(extra=()):
    return ["-c:v", "libx264", "-crf", CRF, "-preset", PRESET, "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", *extra]


def probe(src):
    """Width, height, duration, fps, and whether there is an audio track."""
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", src],
        capture_output=True, text=True, check=True).stdout
    data = json.loads(out)
    v = next((s for s in data["streams"] if s["codec_type"] == "video"), {})
    a = next((s for s in data["streams"] if s["codec_type"] == "audio"), None)
    num, _, den = (v.get("r_frame_rate") or "30/1").partition("/")
    return {
        "width": int(v.get("width", 0)), "height": int(v.get("height", 0)),
        "duration": float(data["format"].get("duration", 0)),
        "fps": (float(num) / float(den or 1)) if den else 30.0,
        "has_audio": a is not None,
    }


# ---- structure --------------------------------------------------------------
def trim(src, dest, start=0.0, end=None, fast=False):
    """Keep [start, end]. `fast` stream-copies - quicker, but cuts snap to keyframes."""
    args = ["-ss", str(start), "-i", src]
    if end is not None:
        args += ["-t", str(max(0.05, end - start))]
    _run(args + (["-c", "copy", "-movflags", "+faststart", dest] if fast else _enc() + [dest]))
    return dest


def cut_out(src, dest, start, end):
    """Remove [start, end] and join the remainder - the cut every talking video needs."""
    d = probe(src)["duration"]
    _run(["-i", src, "-filter_complex",
          f"[0:v]trim=0:{start},setpts=PTS-STARTPTS[v0];"
          f"[0:a]atrim=0:{start},asetpts=PTS-STARTPTS[a0];"
          f"[0:v]trim={end}:{d},setpts=PTS-STARTPTS[v1];"
          f"[0:a]atrim={end}:{d},asetpts=PTS-STARTPTS[a1];"
          f"[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]",
          "-map", "[v]", "-map", "[a]", *_enc(), dest])
    return dest


def concat(clips, dest, width=1080, height=1920, fps=30):
    """Join clips, normalising size and frame rate first so mismatches don't break it."""
    if not clips:
        raise ValueError("nothing to concat")
    ins, parts, labels = [], [], []
    for i, c in enumerate(clips):
        ins += ["-i", c]
        parts.append(
            f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}[v{i}]")
        parts.append(f"[{i}:a]aresample=async=1[a{i}]")
        labels.append(f"[v{i}][a{i}]")
    parts.append(f"{''.join(labels)}concat=n={len(clips)}:v=1:a=1[v][a]")
    _run([*ins, "-filter_complex", ";".join(parts),
          "-map", "[v]", "-map", "[a]", *_enc(), dest])
    return dest


def crossfade(a, b, dest, duration=0.5):
    """Dissolve a into b. Reads far more considered than a hard cut on a topic change."""
    off = max(0.0, probe(a)["duration"] - duration)
    _run(["-i", a, "-i", b, "-filter_complex",
          f"[0:v][1:v]xfade=transition=fade:duration={duration}:offset={off}[v];"
          f"[0:a][1:a]acrossfade=d={duration}[a]",
          "-map", "[v]", "-map", "[a]", *_enc(), dest])
    return dest


# ---- timing -----------------------------------------------------------------
def speed(src, dest, factor=1.25):
    """>1 faster. Audio is corrected too, chained because atempo caps at 2x per pass."""
    tempo, remaining = [], factor
    while remaining > 2.0:
        tempo.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        tempo.append("atempo=0.5")
        remaining /= 0.5
    tempo.append(f"atempo={remaining:.4f}")
    _run(["-i", src, "-filter_complex",
          f"[0:v]setpts={1 / factor:.6f}*PTS[v];[0:a]{','.join(tempo)}[a]",
          "-map", "[v]", "-map", "[a]", *_enc(), dest])
    return dest


def reverse(src, dest):
    _run(["-i", src, "-vf", "reverse", "-af", "areverse", *_enc(), dest])
    return dest


def loop(src, dest, times=2):
    _run(["-stream_loop", str(times - 1), "-i", src, *_enc(), dest])
    return dest


def freeze_frame(src, dest, at, hold=1.0):
    """Hold a moment - useful for landing a punchline before moving on."""
    _run(["-i", src, "-vf",
          f"select='if(lt(t,{at}),1,if(lt(t,{at + hold}),0,1))',setpts=N/FRAME_RATE/TB",
          "-af", f"aselect='if(lt(t,{at}),1,if(lt(t,{at + hold}),0,1))',asetpts=N/SR/TB",
          *_enc(), dest])
    return dest


# ---- compositing ------------------------------------------------------------
def overlay(base, top, dest, x="(W-w)/2", y="(H-h)/2", start=None, end=None, scale=None):
    """Put `top` (image or video) over `base`, optionally only between start and end."""
    filt = "[1:v]" + (f"scale={scale}," if scale else "") + "null[t];"
    enable = ""
    if start is not None:
        enable = (f":enable='between(t,{start},{end})'" if end is not None
                  else f":enable='gte(t,{start})'")
    _run(["-i", base, "-i", top, "-filter_complex",
          f"{filt}[0:v][t]overlay={x}:{y}{enable}[v]",
          "-map", "[v]", "-map", "0:a?", *_enc(), dest])
    return dest


def picture_in_picture(base, inset, dest, size=0.3, margin=40, corner="br"):
    pos = {"br": (f"W-w-{margin}", f"H-h-{margin}"), "bl": (f"{margin}", f"H-h-{margin}"),
           "tr": (f"W-w-{margin}", f"{margin}"), "tl": (f"{margin}", f"{margin}")}[corner]
    w = int(probe(base)["width"] * size)
    return overlay(base, inset, dest, x=pos[0], y=pos[1], scale=f"{w}:-1")


def watermark(src, logo, dest, opacity=0.75, margin=40, corner="br", width=160):
    pos = {"br": (f"W-w-{margin}", f"H-h-{margin}"), "bl": (f"{margin}", f"H-h-{margin}"),
           "tr": (f"W-w-{margin}", f"{margin}"), "tl": (f"{margin}", f"{margin}")}[corner]
    _run(["-i", src, "-i", logo, "-filter_complex",
          f"[1:v]scale={width}:-1,format=rgba,colorchannelmixer=aa={opacity}[wm];"
          f"[0:v][wm]overlay={pos[0]}:{pos[1]}[v]",
          "-map", "[v]", "-map", "0:a?", *_enc(), dest])
    return dest


def chroma_key(fg, bg, dest, colour="0x00FF00", similarity=0.18, blend=0.05):
    """Green-screen `fg` onto `bg`. Raise `similarity` if edges keep fringes."""
    _run(["-i", bg, "-i", fg, "-filter_complex",
          f"[1:v]chromakey={colour}:{similarity}:{blend}[ck];"
          f"[0:v][ck]overlay[v]",
          "-map", "[v]", "-map", "1:a?", *_enc(), dest])
    return dest


def split_screen(left, right, dest, width=1080, height=1920):
    """Stack two sources top/bottom in a vertical frame - good for before/after."""
    half = height // 2
    _run(["-i", left, "-i", right, "-filter_complex",
          f"[0:v]scale={width}:{half}:force_original_aspect_ratio=increase,"
          f"crop={width}:{half}[t];"
          f"[1:v]scale={width}:{half}:force_original_aspect_ratio=increase,"
          f"crop={width}:{half}[b];[t][b]vstack=inputs=2[v]",
          "-map", "[v]", "-map", "0:a?", *_enc(), dest])
    return dest


# ---- framing and look -------------------------------------------------------
def crop_aspect(src, dest, aspect=9 / 16, anchor="center"):
    d = probe(src)
    tw, th = d["width"], int(d["width"] / aspect)
    if th > d["height"]:
        th, tw = d["height"], int(d["height"] * aspect)
    x = {"center": "(in_w-out_w)/2", "left": "0", "right": "in_w-out_w"}[anchor]
    _run(["-i", src, "-vf", f"crop={tw}:{th}:{x}:(in_h-out_h)/2", *_enc(), dest])
    return dest


def rotate(src, dest, degrees=90):
    vf = {90: "transpose=1", 180: "transpose=1,transpose=1", 270: "transpose=2"}.get(
        degrees % 360, f"rotate={degrees}*PI/180")
    _run(["-i", src, "-vf", vf, *_enc(), dest])
    return dest


def flip(src, dest, horizontal=True):
    _run(["-i", src, "-vf", "hflip" if horizontal else "vflip", *_enc(), dest])
    return dest


def grade(src, dest, brightness=0.0, contrast=1.0, saturation=1.0, gamma=1.0, warmth=0):
    """Colour correction. `warmth` shifts toward orange (+) or blue (-), roughly -50..50."""
    vf = (f"eq=brightness={brightness}:contrast={contrast}:"
          f"saturation={saturation}:gamma={gamma}")
    if warmth:
        k = warmth / 100.0
        vf += f",colorbalance=rs={k}:bs={-k}"
    _run(["-i", src, "-vf", vf, *_enc(), dest])
    return dest


def fade(src, dest, fade_in=0.5, fade_out=0.5):
    d = probe(src)["duration"]
    vf = f"fade=t=in:st=0:d={fade_in},fade=t=out:st={max(0, d - fade_out)}:d={fade_out}"
    af = f"afade=t=in:st=0:d={fade_in},afade=t=out:st={max(0, d - fade_out)}:d={fade_out}"
    _run(["-i", src, "-vf", vf, "-af", af, *_enc(), dest])
    return dest


def vignette(src, dest, strength=0.6):
    _run(["-i", src, "-vf", f"vignette=PI/{max(2.0, 6 - strength * 4):.2f}", *_enc(), dest])
    return dest


def blur_background_pad(src, dest, width=1080, height=1920):
    """Fit any aspect into a vertical frame with a blurred fill instead of black bars."""
    _run(["-i", src, "-filter_complex",
          f"split[a][b];[a]scale={width}:{height}:force_original_aspect_ratio=increase,"
          f"crop={width}:{height},boxblur=luma_radius=45:luma_power=2[bg];"
          f"[b]scale={width}:-1[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2[v]",
          "-map", "[v]", "-map", "0:a?", *_enc(), dest])
    return dest


# ---- furniture --------------------------------------------------------------
def burn_text(src, dest, text, size=54, colour="white", box=True, y="h-320",
              x="(w-text_w)/2", start=None, end=None, font=None):
    """Burn a line into the picture. Escaping matters - colons and quotes break drawtext."""
    safe = text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’")
    opts = [f"text='{safe}'", f"fontsize={size}", f"fontcolor={colour}", f"x={x}", f"y={y}"]
    font = font or _default_font()
    if font:
        # Forward slashes, and the drive-letter colon must be escaped or ffmpeg reads
        # it as the start of the next filter option.
        safe_font = font.replace(chr(92), "/").replace(":", r"\:")
        opts.append(f"fontfile='{safe_font}'")
    if box:
        opts += ["box=1", "boxcolor=black@0.55", "boxborderw=18"]
    if start is not None:
        opts.append(f"enable='between(t,{start},{end if end is not None else 1e6})'")
    _run(["-i", src, "-vf", "drawtext=" + ":".join(opts), *_enc(), dest])
    return dest


def progress_bar(src, dest, height=10, colour="white@0.9"):
    """A thin bar that fills as the video plays. Measurably helps completion rate."""
    d = probe(src)
    _run(["-i", src, "-vf",
          f"drawbox=x=0:y=ih-{height}:w='iw*t/{d['duration']:.3f}':h={height}:"
          f"color={colour}:t=fill",
          *_enc(), dest])
    return dest


# ---- export -----------------------------------------------------------------
def to_gif(src, dest, fps=12, width=480, start=0, duration=None):
    """Two-pass palette GIF - one pass looks like 1998."""
    palette = dest + ".png"
    trim_args = ["-ss", str(start)] + (["-t", str(duration)] if duration else [])
    _run([*trim_args, "-i", src, "-vf",
          f"fps={fps},scale={width}:-1:flags=lanczos,palettegen", palette])
    _run([*trim_args, "-i", src, "-i", palette, "-filter_complex",
          f"fps={fps},scale={width}:-1:flags=lanczos[x];[x][1:v]paletteuse", dest])
    os.remove(palette)
    return dest


def extract_frames(src, out_dir, every=1.0):
    os.makedirs(out_dir, exist_ok=True)
    _run(["-i", src, "-vf", f"fps=1/{every}", os.path.join(out_dir, "frame_%04d.png")])
    return out_dir


def contact_sheet(src, dest, cols=4, rows=5):
    """One image of the whole video - the fastest way to eyeball a render for faults."""
    d = probe(src)
    step = max(0.1, d["duration"] / (cols * rows))
    _run(["-i", src, "-vf",
          f"fps=1/{step},scale=320:-1,tile={cols}x{rows}", "-frames:v", "1", dest])
    return dest
