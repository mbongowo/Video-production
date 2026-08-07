"""Optional polish, each step a well-known free/open tool used as a subprocess.

Nothing here is required and nothing here costs money. Each function checks whether
its tool is installed and tells you how to get it if not, so the pipeline degrades
politely instead of exploding.

    auto-editor    MIT/Unlicense  cuts silence and dead air out of talking footage
    rembg          MIT            removes a background (green-screen without a screen)
    Real-ESRGAN    BSD-3          upscales footage or stills 2-4x
    RIFE           MIT            interpolates frames for smooth slow motion
    Demucs         MIT            splits music from speech in a source recording
    faster-whisper MIT            transcription for captions (see ccvp/captions.py)

All of these are separate executables. Calling them does not affect this package's
MIT licence - see COMMERCIAL-USE.md.
"""

import os
import shutil
import subprocess

TOOLS = {
    "auto-editor": "pip install auto-editor",
    "rembg": "pip install rembg[cli]",
    "realesrgan-ncnn-vulkan": "https://github.com/xinntao/Real-ESRGAN/releases",
    "rife-ncnn-vulkan": "https://github.com/nihui/rife-ncnn-vulkan/releases",
    "demucs": "pip install demucs",
}


def available():
    """Which optional tools are installed. Handy for a setup check."""
    return {name: bool(shutil.which(name)) for name in TOOLS}


def _need(tool):
    exe = shutil.which(tool)
    if not exe:
        raise RuntimeError(f"{tool} not found. Install it: {TOOLS.get(tool, '')}")
    return exe


def trim_silence(src, dest, threshold=0.04, margin="0.2sec"):
    """Cut dead air. The single biggest improvement to talking-head footage."""
    exe = _need("auto-editor")
    subprocess.run([exe, src, "--edit", f"audio:threshold={threshold}",
                    "--margin", margin, "-o", dest], check=True)
    return dest


def remove_background(image_or_video, dest):
    """Strip the background from a still. Pair with a template to drop a presenter
    over your own graphics without a physical green screen."""
    exe = _need("rembg")
    subprocess.run([exe, "i", image_or_video, dest], check=True)
    return dest


def upscale(src, dest, scale=2):
    """2-4x upscale. Useful when your only footage is an old phone clip."""
    exe = _need("realesrgan-ncnn-vulkan")
    subprocess.run([exe, "-i", src, "-o", dest, "-s", str(scale)], check=True)
    return dest


def interpolate(src, dest, factor=2):
    """Double the frame rate for smooth slow motion without a high-speed camera."""
    exe = _need("rife-ncnn-vulkan")
    subprocess.run([exe, "-i", src, "-o", dest, "-n", str(factor)], check=True)
    return dest


def split_stems(audio, out_dir):
    """Separate vocals from music - e.g. to rescue narration from a noisy recording."""
    exe = _need("demucs")
    subprocess.run([exe, "-o", out_dir, audio], check=True)
    return out_dir


def loudness_normalise(src, dest, target_lufs=-14.0):
    """Match the loudness platforms normalise to. Pure ffmpeg, always available.

    -14 LUFS is what YouTube, Spotify and most feeds target. Delivering louder just
    means the platform turns you down and you lose dynamic range for nothing.
    """
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src,
                    "-af", f"loudnorm=I={target_lufs}:TP=-1.5:LRA=11",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                    "-movflags", "+faststart", dest], check=True)
    return dest


def to_square(src, dest, size=1080):
    """1:1 crop for feed posts, from the same vertical master."""
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src,
                    "-vf", f"crop=in_w:in_w,scale={size}:{size}",
                    "-c:a", "copy", "-movflags", "+faststart", dest], check=True)
    return dest


def to_landscape(src, dest, width=1920, height=1080, blur=True):
    """16:9 version for YouTube proper, with the vertical frame centred.

    Blurred pillarbox rather than black bars - it reads as deliberate rather than
    like an upload mistake.
    """
    if blur:
        vf = (f"split[a][b];[a]scale={width}:{height},boxblur=luma_radius=40:"
              f"luma_power=2[bg];[b]scale=-1:{height}[fg];[bg][fg]overlay=(W-w)/2:0")
    else:
        vf = f"scale=-1:{height},pad={width}:{height}:(ow-iw)/2:0:black"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src,
                    "-filter_complex", vf, "-c:a", "copy",
                    "-movflags", "+faststart", dest], check=True)
    return dest
