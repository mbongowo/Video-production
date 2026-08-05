"""Free stock photos and video clips, from sources that allow commercial use.

Two providers, both free, both with keys you get in a minute and never pay for:

  Pexels   https://www.pexels.com/api/      set PEXELS_API_KEY
  Pixabay  https://pixabay.com/api/docs/    set PIXABAY_API_KEY

These are **content licences, not software licences**. Both allow commercial use and
neither requires attribution, but both forbid reselling the raw asset, and both put
the burden on you for identifiable people, logos and trademarks. If a client is
paying for it, read the current terms - they change.

Nothing here is required. The animated templates produce a complete, professional
video with no imagery at all, which is also the only path with zero third-party
content risk.
"""

import os
import urllib.parse
import urllib.request

UA = {"User-Agent": "content-creation-video-pipeline"}
TIMEOUT = 45


def _json(url, headers=None):
    import json
    req = urllib.request.Request(url, headers={**UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.load(r)


def _download(url, dest):
    os.makedirs(os.path.dirname(dest) or ".", exist_ok=True)
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r, open(dest, "wb") as f:
        f.write(r.read())
    return dest


def pexels_photo(query, dest, orientation="portrait", key=None):
    key = key or os.environ.get("PEXELS_API_KEY")
    if not key:
        raise RuntimeError("set PEXELS_API_KEY - free at https://www.pexels.com/api/")
    q = urllib.parse.quote(query)
    data = _json(f"https://api.pexels.com/v1/search?query={q}"
                 f"&orientation={orientation}&per_page=1", {"Authorization": key})
    if not data.get("photos"):
        raise LookupError(f"no Pexels photo for {query!r}")
    photo = data["photos"][0]
    _download(photo["src"]["large2x"], dest)
    return {"file": dest, "credit": photo.get("photographer"), "url": photo.get("url")}


def pexels_video(query, dest, orientation="portrait", key=None):
    key = key or os.environ.get("PEXELS_API_KEY")
    if not key:
        raise RuntimeError("set PEXELS_API_KEY - free at https://www.pexels.com/api/")
    q = urllib.parse.quote(query)
    data = _json(f"https://api.pexels.com/videos/search?query={q}"
                 f"&orientation={orientation}&per_page=1", {"Authorization": key})
    if not data.get("videos"):
        raise LookupError(f"no Pexels video for {query!r}")
    vid = data["videos"][0]
    # Pick the largest file that is still sane to download.
    files = sorted(vid["video_files"], key=lambda f: (f.get("height") or 0))
    best = next((f for f in reversed(files) if (f.get("height") or 0) <= 1920), files[-1])
    _download(best["link"], dest)
    return {"file": dest, "credit": vid.get("user", {}).get("name"), "url": vid.get("url")}


def pixabay_photo(query, dest, key=None):
    key = key or os.environ.get("PIXABAY_API_KEY")
    if not key:
        raise RuntimeError("set PIXABAY_API_KEY - free at https://pixabay.com/api/docs/")
    q = urllib.parse.quote(query)
    data = _json(f"https://pixabay.com/api/?key={key}&q={q}"
                 f"&image_type=photo&orientation=vertical&per_page=3")
    if not data.get("hits"):
        raise LookupError(f"no Pixabay photo for {query!r}")
    hit = data["hits"][0]
    _download(hit["largeImageURL"], dest)
    return {"file": dest, "credit": hit.get("user"), "url": hit.get("pageURL")}


def unsplash_photo(query, dest, key=None):
    key = key or os.environ.get("UNSPLASH_ACCESS_KEY")
    if not key:
        raise RuntimeError("set UNSPLASH_ACCESS_KEY - free at https://unsplash.com/developers")
    q = urllib.parse.quote(query)
    data = _json(f"https://api.unsplash.com/search/photos?query={q}"
                 f"&orientation=portrait&per_page=1", {"Authorization": f"Client-ID {key}"})
    if not data.get("results"):
        raise LookupError(f"no Unsplash photo for {query!r}")
    hit = data["results"][0]
    _download(hit["urls"]["regular"], dest)
    return {"file": dest, "credit": hit["user"]["name"], "url": hit["links"]["html"]}


def commons_media(query, dest, kind="image"):
    """Wikimedia Commons - **no API key at all**, and no signup.

    The only source here you can use with zero accounts. Filters to public domain and
    CC0 only, deliberately skipping CC-BY-SA: share-alike on a media file is a headache
    you do not want inside a video you sell. Huge archival and educational collection.
    """
    mime = "image" if kind == "image" else "video"
    q = urllib.parse.quote(f"{query} filetype:{'bitmap' if mime == 'image' else 'video'}")
    data = _json("https://commons.wikimedia.org/w/api.php?action=query&generator=search"
                 f"&gsrsearch={q}&gsrnamespace=6&gsrlimit=12&prop=imageinfo"
                 "&iiprop=url|extmetadata|size&iiurlwidth=1600&format=json")
    pages = (data.get("query") or {}).get("pages") or {}
    for page in pages.values():
        info = (page.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        licence = (meta.get("LicenseShortName", {}).get("value") or "").lower()
        if not any(t in licence for t in ("public domain", "cc0", "pd-")):
            continue                      # skip CC-BY-SA and anything unclear
        url = info.get("thumburl") or info.get("url")
        if not url:
            continue
        _download(url, dest)
        return {"file": dest, "licence": licence,
                "credit": (meta.get("Artist", {}).get("value") or "").strip(),
                "url": info.get("descriptionurl")}
    raise LookupError(f"no public-domain/CC0 Commons media for {query!r}")


def credits_block(assets):
    """A creditline you can paste into the caption. Not required by either licence,
    but it costs you one line and it is how these libraries keep existing."""
    names = sorted({a["credit"] for a in assets if a.get("credit")})
    return ("Footage: " + ", ".join(names) + " (Pexels/Pixabay)") if names else ""
