import json
import urllib.parse

from utils.misc import clean_title, extract_year, extract_episode, infohash_from_magnet, sanitize_field

BASE = "https://torrentapi.org/pubapi_v2.php"


def search(query, net, mode="movie", lang=None, quality=None):
    q = urllib.parse.quote(query)
    data = net.get(
        f"{BASE}?mode=search&search_string={q}&app_id=cinecli",
        source="rarbg",
    )
    if not data:
        return []
    try:
        payload = json.loads(data)
    except Exception:
        return []
    torrents = payload.get("torrent_results") or []
    out = []
    for r in torrents:
        magnet = r.get("download")
        info_hash = infohash_from_magnet(magnet)
        if not info_hash:
            continue
        name = r.get("title") or ""
        title = clean_title(name)
        out.append({
            "source": "rarbg",
            "title": title,
            "year": extract_year(name),
            "quality": _quality(name),
            "size": _size(r.get("size")),
            "info_hash": info_hash,
            "seeders": r.get("seeders") or 0,
            "extra_info": extract_episode(name),
            "score": 0,
            "magnet": magnet,
            "raw": name,
        })
    return out


def _quality(name):
    import re

    m = re.search(r"\b(2160|1080|720|480)p\b", name or "", re.I)
    return m.group(0).lower() if m else "unknown"


def _size(text):
    if not text:
        return "?"
    try:
        return _human(int(text))
    except Exception:
        return str(text)


def _human(n):
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{int(n)} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"
