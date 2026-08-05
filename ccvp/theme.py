"""Look and feel: a bright, readable palette plus text that cannot leave the frame.

Import it *after* manim so the safe `Text` shadows manim's::

    from manim import *
    from ccvp.theme import *

Two of these helpers exist because of bugs that shipped in real videos:

* `Text` shrinks anything wider than the safe width. Hook lines are the usual
  casualty - a long first line gets clipped on both edges and the viewer sees a
  sentence with its first and last letters missing.
* `clamp_x` slides a label back inside the frame *after* it has been positioned.
  `Text` cannot help there: those labels were the right size, they were just
  pushed past the edge by `.next_to()` / `.shift()`. Two of them shipped that
  way and were only caught by rendering and looking.

Backgrounds are light on purpose. A dark render gives the platform nothing but a
black tile to auto-pick as your cover, and on Instagram and TikTok the cover is
chosen at upload and is permanent.
"""

from manim import (
    Text as _ManimText, Line, VGroup, FadeIn, BOLD, UP, DOWN, LEFT, RIGHT, config,
)

__all__ = [
    "BG", "INK", "ACCENT", "WARN", "COOL", "WARM", "MUTED", "MUTED_FILL", "ON_FILL",
    "DARK_BG", "DARK_INK", "SAFE_W", "fit", "clamp_x", "Text", "brand_chip",
    "outro_card", "set_accent",
]

# --- palette -----------------------------------------------------------------
# Light page, dark ink. Every accent is picked to stay readable against BG.
BG = "#f4f6f5"          # page
INK = "#16211d"         # body text
ACCENT = "#0a7d4d"      # brand colour - override per video with set_accent()
WARN = "#c62828"        # the problem / the myth / the "don't"
COOL = "#1565c0"        # secondary highlight
WARM = "#a9741a"        # tertiary highlight
MUTED = "#5d6d67"       # captions, outlines. manim's GREY_B (#BBB) vanishes on light
MUTED_FILL = "#ccd6d2"  # panel fills - always pair with a MUTED stroke
ON_FILL = "#ffffff"     # text sitting on a saturated fill

# For the occasional shot that is *about* darkness (night, sleep, space, screens).
DARK_BG = "#0b0f14"
DARK_INK = "#eef4f2"

# 1080px of frame = 8.0 world units. 7.2 leaves a 5% margin each side.
SAFE_W = 7.2


def set_accent(hex_colour):
    """Point the palette at this video's brand colour."""
    global ACCENT
    if hex_colour:
        ACCENT = hex_colour
    return ACCENT


# --- text that stays inside the frame ----------------------------------------
def fit(mob, width=SAFE_W):
    """Scale a mobject down if it is wider than the safe width. Never scales up."""
    if mob.width > width:
        mob.scale(width / mob.width)
    return mob


def clamp_x(mob, margin=0.4):
    """Slide a mobject horizontally until it sits inside the frame.

    Call this AFTER positioning. `fit` handles labels that are too wide; this
    handles ones that are the right size but got pushed past an edge.
    """
    limit = config.frame_width / 2 - margin
    over_right = mob.get_right()[0] - limit
    if over_right > 0:
        mob.shift(LEFT * over_right)
    over_left = -limit - mob.get_left()[0]
    if over_left > 0:
        mob.shift(RIGHT * over_left)
    return mob


class Text(_ManimText):
    """manim's Text, defaulted to INK and shrunk to fit inside the frame."""

    def __init__(self, text, **kwargs):
        kwargs.setdefault("color", INK)
        super().__init__(text, **kwargs)
        fit(self)


# --- shared furniture --------------------------------------------------------
def brand_chip(handle, accent=None):
    """Small handle label for the top of the frame. Returns a mobject; you place it."""
    accent = accent or ACCENT
    dot = Line(LEFT * 0.08, RIGHT * 0.08, color=accent, stroke_width=10)
    name = Text(handle, font_size=26, color=MUTED)
    return VGroup(dot, name).arrange(RIGHT, buff=0.18)


def outro_card(scene, cta="Follow for more", brand="", accent=None, hold=1.6):
    """Closing card. Keep the CTA to one action - a second one splits the click."""
    accent = accent or ACCENT
    parts = []
    if brand:
        parts.append(Text(brand, font_size=40, color=INK, weight=BOLD))
    parts.append(Line(LEFT * 2.2, RIGHT * 2.2, color=accent, stroke_width=3))
    parts.append(Text(cta, font_size=34, color=accent, weight=BOLD))
    grp = VGroup(*parts).arrange(DOWN, buff=0.35)
    scene.play(FadeIn(grp, shift=UP * 0.3), run_time=0.7)
    scene.wait(hold)
