"""One spec in, a finished short plus its cover and a QA verdict out.

    python make.py examples/morning_routine.json

Stages: read spec -> voice every beat -> render the animation (holding each beat
for its narration) -> mux voice + music -> cut the cover -> run the checks.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys

from ccvp import assemble, music, qa, thumbnail, voice

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
OUT = os.path.join(ROOT, "out")


def spoken_lines(spec):
    """The narration script, one line per beat: hook, each point, then the outro.

    A point is spoken as its `say` if given, otherwise label + note - so you can
    write tight on-screen text and still have the voice read a full sentence.
    """
    lines = [spec["hook"]]
    for p in spec.get("points", []):
        say = p.get("say")
        if not say:
            say = ". ".join(x for x in (p.get("label"), p.get("note")) if x)
        lines.append(say)
    if spec.get("outro"):
        lines.append(spec["outro"])
    return lines


def require_tools():
    missing = [t for t in ("ffmpeg", "ffprobe") if not shutil.which(t)]
    if missing:
        raise SystemExit(f"missing on PATH: {', '.join(missing)} - see README (Install)")


def build(spec_path, deep_qa=False, keep=False):
    require_tools()
    spec = json.load(open(spec_path, encoding="utf-8"))
    vid = spec.get("id") or os.path.splitext(os.path.basename(spec_path))[0]
    work = os.path.join(BUILD, vid)
    os.makedirs(work, exist_ok=True)
    os.makedirs(OUT, exist_ok=True)

    # 1. voice ---------------------------------------------------------------
    print(f"[1/5] narration ({spec.get('engine', 'edge')})")
    clips = voice.narrate(spoken_lines(spec), os.path.join(work, "narration"),
                          voice=spec.get("voice"), rate=spec.get("rate", "-5%"),
                          engine=spec.get("engine", "edge"),
                          # A commercial build must never quietly fall back to edge.
                          allow_fallback=not spec.get("commercial"))

    # 2. animation -----------------------------------------------------------
    print("[2/5] animation")
    resolved = dict(spec)
    resolved["beats"] = [{"text": c["text"], "duration": c["duration"]} for c in clips]
    resolved_path = os.path.join(work, "resolved.json")
    timeline_path = os.path.join(work, "timeline.json")
    json.dump(resolved, open(resolved_path, "w", encoding="utf-8"), indent=1)

    env = dict(os.environ, CCVP_SPEC=resolved_path, CCVP_TIMELINE=timeline_path,
               PYTHONPATH=ROOT + os.pathsep + os.environ.get("PYTHONPATH", ""))
    subprocess.run([sys.executable, "-m", "manim", "-r", "1080,1920", "--fps", "30",
                    "-qh", "--disable_caching", "--media_dir", os.path.join(work, "media"),
                    os.path.join(ROOT, "ccvp", "templates.py"), "Short"],
                   check=True, env=env, cwd=ROOT)
    silent = os.path.join(work, "media", "videos", "templates", "1920p30", "Short.mp4")
    if not os.path.exists(silent):
        raise SystemExit(f"manim produced no file at {silent}")
    marks, total = assemble.load_timeline(timeline_path)

    # 3. music ---------------------------------------------------------------
    print("[3/5] music bed")
    bed = music.bed(os.path.join(work, "bed.wav"),
                    seconds=max(32.0, total + 2), mood=spec.get("mood", "calm"))

    # 4. mux + cover ---------------------------------------------------------
    print("[4/5] mix and cover")
    final = os.path.join(OUT, f"{vid}.mp4")
    assemble.mux(silent, clips, marks, bed, final, total=total)
    # Cut the cover late in the last body beat. The hook stays on screen through the
    # body, so that frame carries the hook AND the filled-in points - cutting during
    # beat 0 gives a technically-correct cover that is mostly empty space.
    n_points = len(spec.get("points", []))
    if n_points and len(marks) > n_points:
        last_body = marks[n_points]
        ceiling = marks[n_points + 1] if len(marks) > n_points + 1 else total
        cover_at = min(last_body + 1.2, max(last_body + 0.3, ceiling - 0.6))
    else:
        cover_at = min(max(1.2, total / 3), max(0.5, total - 0.5))
    cover_path = os.path.join(OUT, f"{vid}_cover.jpg")
    assemble.cover(final, cover_path, round(cover_at, 2),
                   force_lift=spec.get("dark_on_purpose") or None)
    # Every video gets a YouTube card too - a letterboxed vertical crop reads as
    # an accident, so this one is composed rather than cropped.
    thumb_path = os.path.join(OUT, f"{vid}_thumbnail.jpg")
    thumbnail.youtube_thumbnail(final, thumb_path,
                                spec.get("title") or spec.get("hook", ""),
                                round(cover_at, 2), accent=spec.get("accent", "#0a7d4d"))

    # 5. checks --------------------------------------------------------------
    print("[5/5] checks")
    ok = qa.report(final, spec=spec, cover_path=cover_path, deep=deep_qa)
    for path, size in ((cover_path, (1080, 1920)), (thumb_path, (1280, 720))):
        problem = thumbnail.verify(path, size)
        if problem:
            print(f"  artwork          {problem}")
            ok = False

    if not keep:
        shutil.rmtree(os.path.join(work, "media"), ignore_errors=True)

    print(f"\n  video  {final}")
    print(f"  cover  {cover_path}   (1080x1920 reel/short tile)")
    print(f"  thumb  {thumb_path}   (1280x720 YouTube card)")
    print(f"  title  {spec.get('title', '(none)')}")
    if not ok:
        print("\n  Fix the items above before posting.")
    return final, cover_path, ok


def main():
    ap = argparse.ArgumentParser(description="Build a social short from a JSON spec.")
    ap.add_argument("spec", help="path to a spec .json (see examples/)")
    ap.add_argument("--deep", action="store_true",
                    help="also scan every second for labels clipped at the frame edge")
    ap.add_argument("--keep", action="store_true", help="keep intermediate render files")
    a = ap.parse_args()
    _, _, ok = build(a.spec, deep_qa=a.deep, keep=a.keep)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
