"""Picture editing, on Pillow - already a dependency, so nothing extra to install.

    open_rgb / save / resize_fit / resize_fill / crop_aspect / rotate / flip
    brightness / contrast / saturation / sharpen / blur / grayscale / duotone
    text / headline / watermark / border / rounded / shadow / gradient_scrim
    quote_card / carousel / grid / safe_area_check
    cutout                                    (optional, needs rembg)

The composed helpers - `quote_card`, `carousel`, `headline` - are the ones that save
real time: a carousel post or a quote graphic is otherwise a manual Canva job every
single time.

Sizes worth knowing: 1080x1920 reel/story, 1080x1350 feed portrait, 1080x1080 square,
1280x720 YouTube. `PRESETS` has them.
"""

import os
import textwrap

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

PRESETS = {
    "reel": (1080, 1920), "story": (1080, 1920), "portrait": (1080, 1350),
    "square": (1080, 1080), "youtube": (1280, 720), "landscape": (1920, 1080),
}

FONT_CANDIDATES = [
    r"C:\Windows\Fonts\seguibl.ttf", r"C:\Windows\Fonts\segoeuib.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]
FONT_REGULAR = [
    r"C:\Windows\Fonts\segoeui.ttf", r"C:\Windows\Fonts\arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]

INK = "#16211d"
BG = "#f4f6f5"
ACCENT = "#0a7d4d"


def font(size, bold=True, path=None):
    for p in ([path] if path else []) + (FONT_CANDIDATES if bold else FONT_REGULAR):
        if p and os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except OSError:
                continue
    return ImageFont.load_default()


def open_rgb(path):
    return Image.open(path).convert("RGB")


def save(im, dest, quality=92):
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    im.save(dest, quality=quality)
    return dest


# ---- geometry ---------------------------------------------------------------
def resize_fit(im, size):
    """Whole image inside `size`, padded. Nothing is cropped away."""
    out = Image.new("RGB", size, BG)
    copy = im.copy()
    copy.thumbnail(size, Image.LANCZOS)
    out.paste(copy, ((size[0] - copy.width) // 2, (size[1] - copy.height) // 2))
    return out


def resize_fill(im, size):
    """Fill `size` completely, cropping the overflow. What you want for a cover."""
    return ImageOps.fit(im, size, Image.LANCZOS, centering=(0.5, 0.5))


def crop_aspect(im, aspect=9 / 16, anchor=(0.5, 0.5)):
    w, h = im.size
    tw, th = (w, int(w / aspect)) if int(w / aspect) <= h else (int(h * aspect), h)
    return ImageOps.fit(im, (tw, th), Image.LANCZOS, centering=anchor)


def rotate(im, degrees, expand=True):
    return im.rotate(-degrees, expand=expand, resample=Image.BICUBIC, fillcolor=BG)


def flip(im, horizontal=True):
    return ImageOps.mirror(im) if horizontal else ImageOps.flip(im)


# ---- tone -------------------------------------------------------------------
def brightness(im, factor=1.1):
    return ImageEnhance.Brightness(im).enhance(factor)


def contrast(im, factor=1.15):
    return ImageEnhance.Contrast(im).enhance(factor)


def saturation(im, factor=1.2):
    return ImageEnhance.Color(im).enhance(factor)


def sharpen(im, factor=1.4):
    return ImageEnhance.Sharpness(im).enhance(factor)


def blur(im, radius=6):
    return im.filter(ImageFilter.GaussianBlur(radius))


def grayscale(im):
    return ImageOps.grayscale(im).convert("RGB")


def duotone(im, dark=INK, light=BG):
    """Two-colour treatment. Makes mismatched stock photos look like one set."""
    return ImageOps.colorize(ImageOps.grayscale(im), black=dark, white=light).convert("RGB")


# ---- furniture --------------------------------------------------------------
def gradient_scrim(im, height=0.45, colour=(0, 0, 0), max_alpha=210, top=False):
    """Darken one end so text reads over any photo. The reason captions stay legible."""
    w, h = im.size
    band = int(h * height)
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    for i in range(band):
        a = int(max_alpha * (i / band) ** 1.4)
        y = i if top else h - 1 - i
        draw.line([(0, y), (w, y)], fill=(*colour, a))
    return Image.alpha_composite(im.convert("RGBA"), layer).convert("RGB")


def text(im, body, xy, size=54, colour="white", bold=True, outline=None,
         anchor="la", max_chars=None, spacing=12, font_path=None):
    im = im.copy()
    draw = ImageDraw.Draw(im)
    f = font(size, bold, font_path)
    if max_chars:
        body = "\n".join(textwrap.wrap(body, max_chars))
    if outline:
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            draw.multiline_text((xy[0] + dx, xy[1] + dy), body, font=f, fill=outline,
                                anchor=anchor, spacing=spacing)
    draw.multiline_text(xy, body, font=f, fill=colour, anchor=anchor, spacing=spacing)
    return im


def headline(im, body, size=None, colour="white", pad=70, position="bottom",
             max_chars=22, font_path=None):
    """A scrim plus a shrink-to-fit headline. The everyday 'put words on a photo' job."""
    w, h = im.size
    im = gradient_scrim(im, top=(position == "top"))
    size = size or int(w * 0.075)
    draw = ImageDraw.Draw(im)
    while size > 18:
        f = font(size, True, font_path)
        wrapped = "\n".join(textwrap.wrap(body, max_chars))
        box = draw.multiline_textbbox((0, 0), wrapped, font=f, spacing=12)
        if box[2] - box[0] <= w - pad * 2 and box[3] - box[1] <= h * 0.34:
            break
        size -= 3
    th = box[3] - box[1]
    y = pad if position == "top" else h - th - pad - 40
    return text(im, wrapped, (pad, y), size=size, colour=colour, max_chars=max_chars,
                font_path=font_path)


def watermark(im, logo_path=None, handle=None, corner="br", margin=44, opacity=0.8,
              size=140):
    im = im.convert("RGBA")
    w, h = im.size
    if logo_path and os.path.exists(logo_path):
        logo = Image.open(logo_path).convert("RGBA")
        logo.thumbnail((size, size), Image.LANCZOS)
        alpha = logo.split()[3].point(lambda p: int(p * opacity))
        logo.putalpha(alpha)
        pos = {"br": (w - logo.width - margin, h - logo.height - margin),
               "bl": (margin, h - logo.height - margin),
               "tr": (w - logo.width - margin, margin), "tl": (margin, margin)}[corner]
        im.alpha_composite(logo, pos)
    if handle:
        im = text(im.convert("RGB"), handle,
                  (margin, h - margin - 30) if corner.startswith("b") else (margin, margin),
                  size=28, colour="white", outline="#00000088").convert("RGBA")
    return im.convert("RGB")


def border(im, width=18, colour=BG):
    return ImageOps.expand(im, border=width, fill=colour)


def rounded(im, radius=48):
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, *im.size], radius=radius, fill=255)
    out = Image.new("RGB", im.size, BG)
    out.paste(im, mask=mask)
    return out


def shadow(im, offset=(0, 14), blur_radius=22, colour=(0, 0, 0, 90), pad=60):
    base = Image.new("RGBA", (im.width + pad * 2, im.height + pad * 2), (0, 0, 0, 0))
    shade = Image.new("RGBA", im.size, colour)
    base.paste(shade, (pad + offset[0], pad + offset[1]))
    base = base.filter(ImageFilter.GaussianBlur(blur_radius))
    base.paste(im.convert("RGBA"), (pad, pad))
    out = Image.new("RGB", base.size, BG)
    out.paste(base, mask=base.split()[3])
    return out


# ---- composed formats -------------------------------------------------------
def quote_card(body, dest, attribution=None, size="square", accent=ACCENT,
               bg=BG, ink=INK, font_path=None):
    """A quote graphic. Shrinks the text until it fits rather than overflowing."""
    w, h = PRESETS.get(size, PRESETS["square"])
    im = Image.new("RGB", (w, h), bg)
    draw = ImageDraw.Draw(im)
    draw.rectangle([70, 70, 70 + 110, 70 + 14], fill=accent)

    fs = int(w * 0.075)
    while fs > 20:
        f = font(fs, True, font_path)
        wrapped = "\n".join(textwrap.wrap(body, max(14, int(w / (fs * 0.55)))))
        box = draw.multiline_textbbox((0, 0), wrapped, font=f, spacing=16)
        if box[2] - box[0] <= w - 140 and box[3] - box[1] <= h * 0.55:
            break
        fs -= 3
    th = box[3] - box[1]
    draw.multiline_text((70, (h - th) // 2), wrapped, font=f, fill=ink, spacing=16)
    if attribution:
        draw.text((70, h - 110), attribution, font=font(int(w * 0.032), False, font_path),
                  fill=accent)
    return save(im, dest)


def carousel(slides, out_dir, prefix="slide", size="portrait", accent=ACCENT,
             bg=BG, ink=INK, brand=None, font_path=None):
    """A multi-slide carousel: {"title", "body"} per slide, numbered automatically.

    Carousels reliably out-perform single images because each swipe is another
    engagement signal. Doing them by hand is why people stop making them.
    """
    w, h = PRESETS.get(size, PRESETS["portrait"])
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for i, slide in enumerate(slides, start=1):
        im = Image.new("RGB", (w, h), bg)
        draw = ImageDraw.Draw(im)
        draw.rectangle([0, 0, w, 12], fill=accent)
        draw.text((70, 80), f"{i}/{len(slides)}", font=font(int(w * 0.035), True, font_path),
                  fill=accent)

        title = slide.get("title", "")
        body = slide.get("body", "")
        y = int(h * 0.22)
        if title:
            ts = int(w * 0.072)
            wrapped = "\n".join(textwrap.wrap(title, max(12, int(w / (ts * 0.55)))))
            draw.multiline_text((70, y), wrapped, font=font(ts, True, font_path),
                                fill=ink, spacing=14)
            y += draw.multiline_textbbox((0, 0), wrapped, font=font(ts, True, font_path),
                                         spacing=14)[3] + 46
        if body:
            bs = int(w * 0.042)
            wrapped = "\n".join(textwrap.wrap(body, max(18, int(w / (bs * 0.52)))))
            draw.multiline_text((70, y), wrapped, font=font(bs, False, font_path),
                                fill="#5d6d67", spacing=12)
        if brand:
            draw.text((70, h - 90), brand, font=font(int(w * 0.032), False, font_path),
                      fill="#5d6d67")
        if i < len(slides):
            draw.text((w - 90, h - 96), "→", font=font(int(w * 0.06), True, font_path),
                      fill=accent)
        paths.append(save(im, os.path.join(out_dir, f"{prefix}_{i:02d}.jpg")))
    return paths


def grid(images, dest, cols=2, cell=(540, 540), gap=12, bg=BG):
    rows = (len(images) + cols - 1) // cols
    w = cols * cell[0] + (cols + 1) * gap
    h = rows * cell[1] + (rows + 1) * gap
    out = Image.new("RGB", (w, h), bg)
    for i, path in enumerate(images):
        tile = resize_fill(open_rgb(path) if isinstance(path, str) else path, cell)
        x = gap + (i % cols) * (cell[0] + gap)
        y = gap + (i // cols) * (cell[1] + gap)
        out.paste(tile, (x, y))
    return save(out, dest)


def safe_area_check(im_path, size="reel"):
    """Warn about content the platform UI will cover.

    Roughly: the top ~12% and bottom ~18% of a reel sit under captions, handles and
    buttons. Anything essential in those bands gets hidden on someone's phone.
    """
    im = open_rgb(im_path) if isinstance(im_path, str) else im_path
    w, h = im.size
    expect = PRESETS.get(size)
    problems = []
    if expect and im.size != expect:
        problems.append(f"{im.size} is not the {size} size {expect}")
    return {"size": im.size, "safe_top": int(h * 0.12), "safe_bottom": int(h * 0.82),
            "problems": problems}


def cutout(src, dest):
    """Background removal. Optional - needs `pip install rembg[cli]` (MIT)."""
    try:
        from rembg import remove  # noqa: PLC0415 - optional
    except ImportError as e:
        raise RuntimeError("cutout needs rembg: pip install rembg[cli]") from e
    with open(src, "rb") as f:
        data = remove(f.read())
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    with open(dest, "wb") as f:
        f.write(data)
    return dest
