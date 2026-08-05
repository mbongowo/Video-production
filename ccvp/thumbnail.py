"""Every video gets both cover formats. No exceptions, and no platform defaults.

Two different jobs, two different sizes:

  cover      1080x1920  the vertical tile in a Reels/Shorts/TikTok feed. Pulled from
                        a real frame, so it matches the video.
  thumbnail  1280x720   the YouTube card. NOT a crop of the vertical frame - a
                        composed 16:9 image with the hook set large, because a
                        letterboxed vertical crop reads as an accident.

Why this is not optional: on one real account the single Short shipped with a proper
title and thumbnail took 102 views; three shipped without took 5, 16 and 26. Same
audience, same week. Assembly was the only variable.

Instagram and TikTok covers are chosen at upload and are **permanent** - there is no
fixing one later. Generate before you open the uploader.
"""

import os
import subprocess
import textwrap

from PIL import Image, ImageDraw, ImageFont

# Bold faces to try, best first. Falls back to PIL's bitmap font if none exist.
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\seguibl.ttf",      # Segoe UI Black
    r"C:\Windows\Fonts\segoeuib.ttf",     # Segoe UI Bold
    r"C:\Windows\Fonts\arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]


def _font(size):
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _text_size(draw, text, font):
    box = draw.multiline_textbbox((0, 0), text, font=font, spacing=10)
    return box[2] - box[0], box[3] - box[1]


def grab(video, dest_png, at_seconds):
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{at_seconds}", "-i", video,
                    "-frames:v", "1", "-update", "1", dest_png], check=True)
    return dest_png


def youtube_thumbnail(video, dest_jpg, title, at_seconds, accent="#0a7d4d",
                      bg="#f4f6f5", ink="#16211d"):
    """Compose a 1280x720 card: the frame on the right, the hook set large on the left.

    Keeps the hook readable at the size YouTube actually shows it in a sidebar.
    """
    W, H = 1280, 720
    tmp = dest_jpg + ".frame.png"
    grab(video, tmp, at_seconds)
    frame = Image.open(tmp).convert("RGB")

    card = Image.new("RGB", (W, H), bg)

    # Right third: the vertical frame, cropped to a tall panel so it stays recognisable.
    panel_w = int(W * 0.36)
    # Scale to COVER the panel on both axes - scaling to height alone leaves a
    # vertical frame narrower than the panel and pastes a black bar down the side.
    scale = max(H / frame.height, panel_w / frame.width)
    scaled = frame.resize((max(panel_w, int(frame.width * scale)),
                           max(H, int(frame.height * scale))), Image.LANCZOS)
    left = max(0, (scaled.width - panel_w) // 2)
    top = max(0, (scaled.height - H) // 2)
    card.paste(scaled.crop((left, top, left + panel_w, top + H)), (W - panel_w, 0))

    draw = ImageDraw.Draw(card)
    draw.rectangle([W - panel_w - 6, 0, W - panel_w, H], fill=accent)

    # Left: the hook, shrunk until it fits the available box.
    box_w = W - panel_w - 130
    size = 88
    while size > 30:
        font = _font(size)
        wrapped = "\n".join(textwrap.wrap(title, max(12, int(box_w / (size * 0.52)))))
        tw, th = _text_size(draw, wrapped, font)
        if tw <= box_w and th <= H - 210:
            break
        size -= 4
    draw.multiline_text((70, (H - th) // 2), wrapped, font=font, fill=ink, spacing=10)
    draw.rectangle([70, (H - th) // 2 - 42, 70 + 96, (H - th) // 2 - 30], fill=accent)

    card.save(dest_jpg, quality=92)
    os.remove(tmp)
    return dest_jpg


def verify(path, expect):
    """Guard against the classic mistake: a 1280x720 image used as a reel cover."""
    if not os.path.exists(path):
        return f"missing: {path}"
    size = Image.open(path).size
    return None if size == expect else f"{os.path.basename(path)} is {size}, expected {expect}"
