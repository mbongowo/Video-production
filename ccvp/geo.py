"""Optional geospatial layer: real country borders, real projections, public domain.

Map content outperforms generic stock because it is *specific* - a viewer recognises
their own country. This draws actual Natural Earth geometry rather than a clip-art
world, so the shapes are correct and the projection claims you make are true.

**Why Natural Earth and not OpenStreetMap.** Natural Earth is explicitly public
domain: no attribution, no share-alike, nothing to comply with when you sell the
video. OpenStreetMap is ODbL - usable, but it carries attribution and share-alike
obligations on derived databases. For commercial work, public domain is the clean
choice. Data is fetched once and cached in `assets/`.

The palette is deliberately light. A dark map renders near-black, and then every
cover a platform auto-picks is a black tile - which is exactly the fault this
pipeline exists to prevent.
"""

import json
import math
import os
import urllib.request

# Official Natural Earth vector repository. 110m = small file, right detail for a
# phone screen. Public domain.
SOURCE = ("https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/"
          "geojson/ne_110m_admin_0_countries.geojson")
CACHE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "assets", "ne_110m_countries.geojson")

# Daylight cartography - see the module docstring.
OCEAN = "#cfe4f2"
LAND = "#efe8da"
BORDER = "#94a8b6"

AFRICA = {
    "algeria", "angola", "benin", "botswana", "burkina faso", "burundi", "cameroon",
    "central african rep.", "chad", "congo", "dem. rep. congo", "djibouti", "egypt",
    "eq. guinea", "eritrea", "eswatini", "ethiopia", "gabon", "gambia", "ghana",
    "guinea", "guinea-bissau", "côte d'ivoire", "kenya", "lesotho", "liberia", "libya",
    "madagascar", "malawi", "mali", "mauritania", "morocco", "mozambique", "namibia",
    "niger", "nigeria", "rwanda", "senegal", "sierra leone", "somalia", "somaliland",
    "south africa", "s. sudan", "sudan", "tanzania", "togo", "tunisia", "uganda",
    "w. sahara", "zambia", "zimbabwe",
}


def load_countries():
    """Fetch once, then read from disk forever."""
    if not os.path.exists(CACHE):
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        print(f"  fetching Natural Earth borders (public domain, one time)")
        req = urllib.request.Request(SOURCE, headers={"User-Agent": "ccvp"})
        with urllib.request.urlopen(req, timeout=90) as r:
            open(CACHE, "wb").write(r.read())
    return json.load(open(CACHE, encoding="utf-8"))["features"]


# ---- projections ------------------------------------------------------------
def _mercator(lon, lat):
    lat = max(-82.0, min(82.0, lat))          # Mercator is infinite at the poles
    return math.radians(lon), math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))


def _equirect(lon, lat):
    return math.radians(lon), math.radians(lat)


def _equal_earth(lon, lat):
    """Equal Earth (Šavrič, Patterson & Jenny 2018) - equal-area, and unlike an
    equal-area cylindrical it still looks like a world map."""
    a1, a2, a3, a4 = 1.340264, -0.081106, 0.000893, 0.003796
    t = math.asin(math.sqrt(3) / 2 * math.sin(math.radians(lat)))
    t2 = t * t
    t6 = t2 * t2 * t2
    x = (math.radians(lon) * math.cos(t)) / (
        math.sqrt(3) / 2 * (a1 + 3 * a2 * t2 + t6 * (7 * a3 + 9 * a4 * t2)))
    y = t * (a1 + a2 * t2 + t6 * (a3 + a4 * t2))
    return x, y


PROJECTIONS = {"mercator": _mercator, "equirect": _equirect, "equalEarth": _equal_earth}


def project_all(features, projection="equalEarth"):
    """Return [(name, [ring, ...])] in projected coordinates, plus the bounding box."""
    fn = PROJECTIONS.get(projection, _equal_earth)
    out = []
    xs, ys = [], []
    for f in features:
        name = (f.get("properties") or {}).get("NAME") or ""
        geom = f.get("geometry") or {}
        polys = (geom.get("coordinates") or [])
        if geom.get("type") == "Polygon":
            polys = [polys]
        elif geom.get("type") != "MultiPolygon":
            continue
        rings = []
        for poly in polys:
            if not poly:
                continue
            ring = []
            for lon, lat in poly[0]:
                try:
                    x, y = fn(lon, lat)
                except (ValueError, ZeroDivisionError):
                    continue
                ring.append((x, y))
                xs.append(x)
                ys.append(y)
            if len(ring) >= 3:
                rings.append(ring)
        if rings:
            out.append((name, rings))
    return out, (min(xs), min(ys), max(xs), max(ys))


def world(projection="equalEarth", highlight=None, highlight2=None,
          accent="#0a7d4d", accent2="#1565c0", width=7.2, height=7.6):
    """A Manim VGroup of the world, fitted to `width` x `height`.

    `highlight` / `highlight2` are country names (case-insensitive); the literal
    "africa" expands to the continent.
    """
    from manim import VGroup, Polygon

    hi = {s.lower() for s in (highlight or [])}
    h2 = {s.lower() for s in (highlight2 or [])}
    use_africa = "africa" in h2
    h2 -= {"africa"}

    feats, (x0, y0, x1, y1) = project_all(load_countries(), projection)
    sx = width / max(1e-9, x1 - x0)
    sy = height / max(1e-9, y1 - y0)
    s = min(sx, sy)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2

    group = VGroup()
    for name, rings in feats:
        low = name.lower()
        if low in hi:
            fill = accent
        elif low in h2 or (use_africa and low in AFRICA):
            fill = accent2
        else:
            fill = LAND
        for ring in rings:
            pts = [((x - cx) * s, (y - cy) * s, 0) for x, y in ring]
            if len(pts) < 3:
                continue
            group.add(Polygon(*pts, color=BORDER, stroke_width=0.8,
                              fill_color=fill, fill_opacity=1))
    return group


def ocean_backdrop(group, pad=0.25):
    """A sea-coloured panel behind the landmasses, sized to them."""
    from manim import RoundedRectangle
    return RoundedRectangle(
        width=group.width + pad, height=group.height + pad, corner_radius=0.12,
        color=BORDER, fill_color=OCEAN, fill_opacity=1, stroke_width=2,
    ).move_to(group)
