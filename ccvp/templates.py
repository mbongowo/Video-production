"""The animation templates. One Scene class, four layouts, all driven by JSON.

Manim instantiates a Scene with no arguments, so the spec arrives by environment
variable: CCVP_SPEC points at the resolved spec that build.py writes (the user's
JSON plus a measured duration for every spoken beat).

As it renders, the scene records the exact second each beat begins and writes
those marks to CCVP_TIMELINE. assemble.py then drops each narration clip at its
mark, so picture and voice stay locked without anyone hand-tuning a wait().
"""

import json
import os
import textwrap

from manim import *  # noqa: F401,F403  - manim's DSL is meant to be star-imported
from ccvp.theme import *  # noqa: F401,F403  - shadows Text with the frame-safe one
from ccvp.theme import (
    BG, INK, WARN, COOL, MUTED, MUTED_FILL, ON_FILL, SAFE_W,
    Text, clamp_x, brand_chip, outro_card, set_accent,
)

# Vertical 9:16. 8.0 units wide keeps SAFE_W = 7.2 meaningful.
config.frame_width = 8.0
config.frame_height = 14.22

PAD = 0.45          # breathing room after each spoken beat


def load_spec():
    path = os.environ.get("CCVP_SPEC")
    if not path:
        raise SystemExit("CCVP_SPEC is not set - run through build.py, not manim directly.")
    return json.load(open(path, encoding="utf-8"))


def wrap(text, chars):
    """Break a line so it stacks instead of being shrunk to nothing by fit()."""
    return "\n".join(textwrap.wrap(text, chars)) or text


class Short(Scene):
    """The single entry point. `format` in the spec picks the body layout."""

    # ---- timeline bookkeeping ----------------------------------------------
    def _init_clock(self):
        self.elapsed = 0.0
        self.marks = []

    def _play(self, *anims, run_time=0.5):
        self.play(*anims, run_time=run_time)
        self.elapsed += run_time

    def _wait(self, seconds):
        self.wait(seconds)
        self.elapsed += seconds

    def beat(self, anims, beat, run_time=0.5):
        """Mark where this beat's narration starts, animate, then hold for the voice."""
        self.marks.append(round(self.elapsed, 3))
        self._play(*anims, run_time=run_time)
        self._wait(max(0.25, beat["duration"] + PAD - run_time))

    def _write_timeline(self):
        path = os.environ.get("CCVP_TIMELINE")
        if path:
            json.dump({"marks": self.marks, "total": round(self.elapsed, 3)},
                      open(path, "w", encoding="utf-8"), indent=1)

    # ---- the short ----------------------------------------------------------
    def construct(self):
        self._init_clock()
        spec = load_spec()
        accent = set_accent(spec.get("accent"))
        self.camera.background_color = BG
        beats = spec["beats"]
        points = spec.get("points", [])

        if spec.get("brand"):
            chip = brand_chip(spec["brand"], accent)
            chip.to_edge(UP, buff=0.5)
            self.add(chip)

        # beat 0: the hook
        hook = Text(wrap(spec["hook"], 20), font_size=54, color=INK,
                    weight=BOLD, line_spacing=1.12)
        hook.move_to(UP * 4.6)
        clamp_x(hook)
        self.hook = hook          # layouts position themselves relative to it
        self.beat([Write(hook)], beats[0], run_time=0.9)

        # body
        fmt = spec.get("format", "listicle")
        body_beats = beats[1:1 + len(points)]
        if fmt == "map":
            self._map(points, body_beats, accent, spec)
        else:
            {
                "listicle": self._listicle,
                "howto": self._howto,
                "myth": self._myth,
                "quote": self._quote,
            }.get(fmt, self._listicle)(points, body_beats, accent)

        # closing beat
        self._play(*[FadeOut(m) for m in self.mobjects], run_time=0.5)
        if len(beats) > 1 + len(points):
            line = Text(wrap(spec.get("outro", ""), 24), font_size=40, color=INK,
                        weight=BOLD, line_spacing=1.12).move_to(UP * 1.0)
            self.beat([Write(line)], beats[-1], run_time=0.9)
            self._play(FadeOut(line), run_time=0.4)

        outro_card(self, spec.get("cta", "Follow for more"), spec.get("brand", ""), accent)
        self.elapsed += 0.7 + 1.6  # outro_card's play + hold
        self._write_timeline()

    # ---- layouts ------------------------------------------------------------
    def _rows(self, points, accent):
        """Build the body rows once, fitted to the frame, ready to reveal."""
        rows = VGroup()
        for p in points:
            label = Text(p.get("label", ""), font_size=34, color=accent, weight=BOLD)
            parts = [label]
            if p.get("note"):
                parts.append(Text(wrap(p["note"], 30), font_size=26, color=MUTED,
                                  line_spacing=1.05))
            rows.add(VGroup(*parts).arrange(DOWN, buff=0.16, aligned_edge=LEFT))
        if not len(rows):
            return rows
        rows.arrange(DOWN, buff=0.55, aligned_edge=LEFT)
        if rows.width > SAFE_W:
            rows.scale_to_fit_width(SAFE_W)
        if rows.height > 8.4:          # keep clear of the hook and the bottom edge
            rows.scale_to_fit_height(8.4)
        rows.move_to(DOWN * 0.6)
        return rows

    def _listicle(self, points, beats, accent):
        rows = self._rows(points, accent)
        for row, b in zip(rows, beats):
            self.beat([FadeIn(row, shift=RIGHT * 0.35)], b, run_time=0.45)

    def _howto(self, points, beats, accent):
        rows = self._rows(points, accent)
        track = Line(LEFT * 3.2, RIGHT * 3.2, color=MUTED_FILL, stroke_width=6)
        track.next_to(rows, UP, buff=0.5)
        clamp_x(track)
        self.add(track)
        n = max(1, len(points))
        for i, (row, b) in enumerate(zip(rows, beats)):
            done = Line(track.get_left(),
                        track.get_left() + RIGHT * (track.width * (i + 1) / n),
                        color=accent, stroke_width=6)
            self.beat([FadeIn(row, shift=RIGHT * 0.35), Create(done)], b, run_time=0.5)

    def _myth(self, points, beats, accent):
        """Alternating panels: even entries read as the claim, odd as the correction."""
        panels = VGroup()
        for i, p in enumerate(points):
            colour = WARN if i % 2 == 0 else accent
            tag = Text(p.get("label", "MYTH" if i % 2 == 0 else "REALITY"),
                       font_size=28, color=ON_FILL, weight=BOLD)
            chip = VGroup(
                RoundedRectangle(width=tag.width + 0.6, height=0.62, corner_radius=0.18,
                                 color=colour, fill_color=colour, fill_opacity=1),
                tag,
            )
            body = Text(wrap(p.get("note", ""), 26), font_size=30, color=INK,
                        line_spacing=1.1)
            panels.add(VGroup(chip, body).arrange(DOWN, buff=0.28, aligned_edge=LEFT))
        panels.arrange(DOWN, buff=0.75, aligned_edge=LEFT)
        if panels.width > SAFE_W:
            panels.scale_to_fit_width(SAFE_W)
        if panels.height > 8.4:
            panels.scale_to_fit_height(8.4)
        panels.move_to(DOWN * 0.6)
        for panel, b in zip(panels, beats):
            self.beat([FadeIn(panel, shift=UP * 0.25)], b, run_time=0.5)

    def _map(self, points, beats, accent, spec):
        """Real country borders. Each beat highlights what that point is about.

        A point may carry `highlight` (list of country names, or "africa") and its
        own `projection`, so you can cut from Mercator to an equal-area map and
        show the size distortion rather than assert it.
        """
        from ccvp import geo

        caption = None
        current = None
        for i, (p, b) in enumerate(zip(points, beats)):
            proj = p.get("projection") or spec.get("projection", "equalEarth")
            world = geo.world(projection=proj,
                              highlight=p.get("highlight"),
                              highlight2=p.get("highlight2"),
                              accent=accent, width=SAFE_W, height=6.0)
            sea = geo.ocean_backdrop(world)
            board = VGroup(sea, world)
            # Hang the map off the hook rather than a fixed y - a three-line hook
            # reaches further down the frame than a one-line hook and would collide.
            board.next_to(self.hook, DOWN, buff=0.55)

            label = Text(wrap(p.get("label", ""), 24), font_size=32, color=INK,
                         weight=BOLD, line_spacing=1.1)
            if p.get("note"):
                label = VGroup(label, Text(wrap(p["note"], 30), font_size=26,
                                           color=MUTED, line_spacing=1.05)
                               ).arrange(DOWN, buff=0.18)
            label.next_to(board, DOWN, buff=0.45)
            clamp_x(label)

            if current is None:
                self.beat([FadeIn(board), FadeIn(label)], b, run_time=0.7)
            else:
                # Cross-fade so a projection change reads as one map changing.
                self.beat([FadeOut(current), FadeOut(caption),
                           FadeIn(board), FadeIn(label)], b, run_time=0.7)
            current, caption = board, label

    def _quote(self, points, beats, accent):
        lines = VGroup(*[
            Text(wrap(p.get("note") or p.get("label", ""), 22), font_size=40,
                 color=INK, weight=BOLD, line_spacing=1.12)
            for p in points
        ]).arrange(DOWN, buff=0.7)
        if lines.height > 8.0:
            lines.scale_to_fit_height(8.0)
        lines.move_to(DOWN * 0.4)
        bar = Line(UP * 0.6, DOWN * 0.6, color=accent, stroke_width=6)
        bar.set_height(lines.height).next_to(lines, LEFT, buff=0.35)
        clamp_x(bar)
        self._play(Create(bar), run_time=0.4)
        for line, b in zip(lines, beats):
            self.beat([FadeIn(line, shift=UP * 0.2)], b, run_time=0.5)
