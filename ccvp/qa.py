"""Automated checks that catch the things eyeballing misses.

Every check here exists because the same fault shipped in a real video:

* `edge_clipping` - labels running off the side of the frame. Reviewing four
  videos by eye missed two of them; this found both in one pass.
* `luma` - a render so dark that every auto-picked cover is a black tile. On
  Instagram and TikTok the cover is set at upload and is permanent.
* `preflight` - posts that went out with an empty caption, or with a filename or
  a date as the title. The one YouTube Short with a real title and description
  got 102 views; three shipped without got 5, 16 and 26.
"""

import io
import os
import subprocess
from collections import Counter

EDGE_COLS = 6       # how many pixel columns at each side count as "the edge"
EDGE_TOL = 60       # deviation from background that counts as real content
BRIGHT_MIN = 80     # peak luma a normal short should clear


def _frames(path, step=1.0):
    from PIL import Image
    dur = float(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip())
    t = 0.5
    while t < dur - 0.2:
        raw = subprocess.run(
            ["ffmpeg", "-v", "error", "-ss", f"{t}", "-i", path, "-frames:v", "1",
             "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
        if raw:
            yield round(t, 1), Image.open(io.BytesIO(raw)).convert("RGB")
        t += step


def edge_clipping(path, step=1.0):
    """Frames with content touching the left/right edge. Usually a clipped label.

    Full-width design elements (a rule, a ground line) trip this too, so read the
    hits rather than trusting the count blindly.
    """
    hits = []
    for t, im in _frames(path, step):
        w, h = im.size
        px = im.load()
        bg = Counter(im.crop((w // 4, h // 4, 3 * w // 4, 3 * h // 4))
                     .resize((40, 40)).getdata()).most_common(1)[0][0]
        for side, cols in (("L", range(EDGE_COLS)), ("R", range(w - EDGE_COLS, w))):
            worst = max((max(abs(px[x, y][c] - bg[c]) for c in range(3))
                         for x in cols for y in range(0, h, 3)), default=0)
            if worst > EDGE_TOL:
                hits.append({"t": t, "side": side, "delta": worst})
    return hits


def luma(path):
    p = subprocess.run(
        ["ffmpeg", "-v", "error", "-i", path, "-vf",
         "fps=1,signalstats,metadata=print:file=-", "-f", "null", "-"],
        capture_output=True, text=True)
    vals = [float(l.split("=")[-1]) for l in p.stdout.splitlines() if "YAVG" in l]
    return max(vals) if vals else 0.0


# Voice engines that are not safe for work you intend to sell. See LICENSING.md.
RISKY_FOR_COMMERCIAL = {
    "edge": ("edge-tts is GPL-3.0 and drives Microsoft's Read Aloud endpoint "
             "unofficially - Microsoft does not offer it for commercial use"),
    "vibevoice": ("VibeVoice is licensed for research only - its authors do not "
                  "permit commercial deployment"),
}


def preflight(spec, cover_path=None):
    """The ship checklist as code. Returns a list of problems - empty means ship it."""
    problems = []

    # Licence guard: only enforced when you declare the video commercial, so trying
    # the tool out stays frictionless.
    if spec.get("commercial"):
        engine = spec.get("engine", "edge")
        if engine in RISKY_FOR_COMMERCIAL:
            problems.append(
                f"commercial:true but engine is {engine!r} - {RISKY_FOR_COMMERCIAL[engine]}. "
                f"Use \"engine\": \"piper\" (MIT, offline). See LICENSING.md")

    title = (spec.get("title") or "").strip()
    if not title:
        problems.append("title is empty - the hook should be the title")
    elif title.lower().endswith((".mp4", ".mov")) or title.replace("-", "").isdigit():
        problems.append(f"title {title!r} looks like a filename or a date")

    if not (spec.get("caption") or "").strip():
        problems.append("caption is empty - never ship a post with no caption")
    if not (spec.get("cta") or "").strip():
        problems.append("no CTA - one clear action, matched to the platform")

    tags = spec.get("hashtags") or []
    if not 4 <= len(tags) <= 8:
        problems.append(f"{len(tags)} hashtags - aim for 4-8, one broad and several niche")

    if cover_path:
        if not os.path.exists(cover_path):
            problems.append("no cover - the platform will pick one, and it will be bad")
        else:
            from PIL import Image
            if Image.open(cover_path).size != (1080, 1920):
                problems.append("cover is not 1080x1920 - reels and shorts need vertical")
    return problems


def report(video, spec=None, cover_path=None, deep=False):
    """Run everything and print a verdict. Returns True when nothing is wrong."""
    ok = True
    peak = luma(video)
    dark_ok = bool(spec and spec.get("dark_on_purpose"))
    print(f"  peak luma        {peak:.1f}", end="")
    if peak < BRIGHT_MIN and not dark_ok:
        print("  <- TOO DARK: every auto-picked cover will be a black tile")
        ok = False
    else:
        print("  ok" + ("  (dark on purpose)" if dark_ok else ""))

    if deep:
        hits = edge_clipping(video)
        if hits:
            sides = sorted({h["side"] for h in hits})
            print(f"  edge clipping    {len(hits)} frame(s), sides={','.join(sides)}"
                  f"  first={hits[0]}")
            print("                   check for a clipped label; a full-width rule is fine")
        else:
            print("  edge clipping    none")

    if spec is not None:
        problems = preflight(spec, cover_path)
        if problems:
            ok = False
            print("  ship checklist   FAILED")
            for p in problems:
                print(f"                   - {p}")
        else:
            print("  ship checklist   passed")
    return ok
