"""Run a whole content calendar at once, with workers specialised by bottleneck.

    python -m ccvp.batch specs/            # everything in a folder
    python -m ccvp.batch specs/ --voice-workers 6 --render-workers 3

The stages do not compete for the same resource, so they get different pools:

  narration  network-bound (or GPU-bound when cloning). Runs many at once, and it
             is the slow step, so it goes FIRST for every video in the batch.
  rendering  CPU-bound. Manim saturates a core per render, so this pool is small -
             oversubscribing it makes the whole batch slower, not faster.
  finishing  I/O-bound (ffmpeg mux, cover, thumbnail). Cheap, runs wide.

Because narration is cached on disk, a failed batch can be re-run and it will pick
up where it left off rather than re-voicing everything.
"""

import argparse
import concurrent.futures as cf
import glob
import json
import os
import sys
import traceback

from ccvp import build as build_mod
from ccvp import voice


def _specs_in(path):
    if os.path.isdir(path):
        return sorted(glob.glob(os.path.join(path, "*.json")))
    return [path]


def _prewarm_voice(spec_path):
    """Stage 1 agent: get the narration on disk. Network/GPU-bound, safe to run wide."""
    spec = json.load(open(spec_path, encoding="utf-8"))
    vid = spec.get("id") or os.path.splitext(os.path.basename(spec_path))[0]
    out_dir = os.path.join(build_mod.BUILD, vid, "narration")
    voice.narrate(build_mod.spoken_lines(spec), out_dir,
                  voice=spec.get("voice"), rate=spec.get("rate", "-5%"),
                  engine=spec.get("engine", "edge"))
    return spec_path


def _render(spec_path, deep):
    """Stage 2 agent: everything after narration. CPU-bound, so keep this pool small."""
    final, cover, ok = build_mod.build(spec_path, deep_qa=deep)
    return {"spec": spec_path, "video": final, "cover": cover, "ok": ok}


def run(paths, voice_workers=4, render_workers=2, deep=False):
    specs = [s for p in paths for s in _specs_in(p)]
    if not specs:
        raise SystemExit("no .json specs found")
    print(f"batch: {len(specs)} video(s), "
          f"{voice_workers} voice worker(s), {render_workers} render worker(s)\n")

    # Phase 1 - narrate everything first. It is the slow, cacheable step, and doing
    # it up front means the render pool never sits idle waiting on the network.
    print("== narration ==")
    voiced, failed = [], []
    with cf.ThreadPoolExecutor(max_workers=voice_workers) as pool:
        futures = {pool.submit(_prewarm_voice, s): s for s in specs}
        for fut in cf.as_completed(futures):
            spec = futures[fut]
            try:
                voiced.append(fut.result())
                print(f"  voiced   {os.path.basename(spec)}")
            except Exception as e:
                failed.append((spec, f"narration: {e}"))
                print(f"  FAILED   {os.path.basename(spec)}: {e}")

    # Phase 2 - render and finish. Small pool: manim is CPU-hungry.
    print("\n== render + finish ==")
    results = []
    with cf.ThreadPoolExecutor(max_workers=render_workers) as pool:
        futures = {pool.submit(_render, s, deep): s for s in voiced}
        for fut in cf.as_completed(futures):
            spec = futures[fut]
            try:
                r = fut.result()
                results.append(r)
                print(f"  {'ok  ' if r['ok'] else 'WARN'}     {os.path.basename(spec)}")
            except Exception as e:
                failed.append((spec, f"render: {e}"))
                print(f"  FAILED   {os.path.basename(spec)}: {e}")
                traceback.print_exc(limit=1)

    print("\n== summary ==")
    clean = [r for r in results if r["ok"]]
    print(f"  {len(clean)} ready to post")
    if len(results) - len(clean):
        print(f"  {len(results) - len(clean)} built but failed a check - see above")
    for spec, why in failed:
        print(f"  FAILED {os.path.basename(spec)}: {why}")
    return results, failed


def main():
    ap = argparse.ArgumentParser(description="Build many videos with staged workers.")
    ap.add_argument("paths", nargs="+", help="spec .json files, or a folder of them")
    ap.add_argument("--voice-workers", type=int, default=4)
    ap.add_argument("--render-workers", type=int, default=max(1, (os.cpu_count() or 4) // 3),
                    help="keep this low - manim is CPU-bound")
    ap.add_argument("--deep", action="store_true", help="run the edge-clipping scan too")
    a = ap.parse_args()
    _, failed = run(a.paths, a.voice_workers, a.render_workers, a.deep)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
