"""HyperFrames adapter: HTML + GSAP compositions rendered to video.

    HyperFrames   Apache-2.0   https://github.com/heygen-com/hyperframes

Write a scene as an HTML page (titles, cards, callouts, captions, animated graphics),
then render it to MP4, or to a transparent WebM that lays over footage built anywhere
else in this package. It complements Manim rather than replacing it: Manim for maths and
diagrams, HyperFrames for web-style motion graphics and kinetic type.

It is a separate Node.js program called as a subprocess, like every adapter here, so it
does not affect this package's MIT licence (see COMMERCIAL-USE.md). Apache-2.0 allows
commercial use with no per-render fee.

Needs Node.js 22+, FFmpeg and Chrome. Nothing to install by hand: `npx` fetches the CLI
on first use. Rendering is always local here; the HyperFrames `cloud` commands upload
your project to a hosted service and are deliberately not wrapped.

    from ccvp import hyperframes as hf
    hf.available()                       # True if Node 22+ is on PATH
    hf.check("scenes/title")             # lint + browser audit, raises on failure
    hf.render("scenes/title", "out/title.mp4", quality="delivery")
    hf.overlay("scenes/lower_third", "out/lower_third.webm")

Authoring is easiest with an AI agent that has the HyperFrames skill installed
(`claude plugin install hyperframes@hyperframes`).
"""

import os
import re
import shutil
import subprocess

INSTALL = "Install Node.js 22 or newer (https://nodejs.org); npx then fetches hyperframes."


def _npx():
    exe = shutil.which("npx.cmd" if os.name == "nt" else "npx") or shutil.which("npx")
    if not exe:
        raise RuntimeError(f"npx not found. {INSTALL}")
    return exe


def _env(cache_dir=None):
    env = dict(os.environ, HYPERFRAMES_NO_TELEMETRY="1")
    if cache_dir:  # frames are extracted to the temp folder; point it at a roomy drive
        os.makedirs(cache_dir, exist_ok=True)
        env.update(TEMP=cache_dir, TMP=cache_dir, TMPDIR=cache_dir)
    return env


def _run(args, cwd=None, cache_dir=None):
    cmd = [_npx(), "--yes", "hyperframes", *args]
    return subprocess.run(cmd, cwd=cwd, env=_env(cache_dir)).returncode


def available():
    """True if a Node.js new enough for HyperFrames (22+) is on PATH."""
    node = shutil.which("node")
    if not node:
        return False
    out = subprocess.run([node, "--version"], capture_output=True, text=True).stdout
    m = re.match(r"v(\d+)", out.strip())
    return bool(m and int(m.group(1)) >= 22)


def init(project_dir):
    """Scaffold a blank composition at project_dir."""
    parent, name = os.path.split(os.path.abspath(project_dir))
    os.makedirs(parent, exist_ok=True)
    if _run(["init", name, "--non-interactive"], cwd=parent) != 0:
        raise RuntimeError("hyperframes init failed")
    return project_dir


def check(project_dir):
    """Lint plus a browser audit of runtime errors, layout and contrast. Raises on failure."""
    if _run(["check"], cwd=project_dir) != 0:
        raise RuntimeError(f"hyperframes check failed for {project_dir}")


def _render(project_dir, dest, quality, fmt, fps, cache_dir):
    check(project_dir)
    dest = os.path.abspath(dest)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    args = ["render", "--quality", quality, "--output", dest, "--fps", str(fps)]
    if fmt != "mp4":
        args += ["--format", fmt]
    if _run(args, cwd=project_dir, cache_dir=cache_dir) != 0:
        raise RuntimeError("hyperframes render failed")
    if not os.path.exists(dest) or os.path.getsize(dest) == 0:
        raise RuntimeError(f"hyperframes render produced no file at {dest}")
    return dest


def render(project_dir, dest, quality="looks", fps=30, cache_dir=None):
    """Render to MP4. quality: draft (iterate), looks (first real encode), delivery (final)."""
    return _render(project_dir, dest, quality, "mp4", fps, cache_dir)


def overlay(project_dir, dest, quality="looks", fps=30, cache_dir=None):
    """Render to a transparent WebM, to composite over other footage with ffmpeg."""
    return _render(project_dir, dest, quality, "webm", fps, cache_dir)
