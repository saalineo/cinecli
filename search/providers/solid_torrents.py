import json
import urllib.parse

from utils.misc import clean_title, extract_year, extract_episode, infohash_from_magnet, human_size, sanitize_field

BASE = "https://solidtorrents.to"
API = BASE + "/api/v1/search"

CATEGORY = "video"


def search(query, net, mode="movie", lang=None, quality=None):
    q = urllib.parse.quote(query)
    category = CATEGORY
    data = net.get(
        f"{API}?q={q}&category={category}&sort=seeders",
        source="solid",
        headers={"Accept": "application/json"},
    )
    if not data:
        return []
    try:
        payload = json.loads(data)
    except Exception:
        return []
    results = payload.get("results") or []
    out = []
    for r in results:
        name = r.get("title") or r.get("name") or ""
        magnet = r.get("magnet")
        info_hash = infohash_from_magnet(magnet)
        if not info_hash:
            continue
        category_hit = r.get("category") or ""
        if mode == "movie" and "tv" in str(category_hit).lower():
            continue
        title = clean_title(name)
        out.append({
            "source": "solid",
            "title": title,
            "year": extract_year(name),
            "quality": _quality(name),
            "size": human_size(r.get("size")) if r.get("size") else "?",
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
