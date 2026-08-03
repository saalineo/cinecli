import json
import re
import urllib.parse

from utils.misc import clean_title, extract_year, extract_episode, sanitize_field

MIRRORS = ["https://apibay.org"]

MOVIE_CATS = {"201", "202", "203", "204", "207", "209", "210", "211"}
TV_CATS = {"205", "208", "209", "210", "211", "212", "213"}


def _quality(name):
    m = re.search(r"\b(2160|1080|720|480)p\b", name or "", re.I)
    return m.group(0).lower() if m else "unknown"


def _parse(data, mode):
    try:
        rows = json.loads(data)
    except Exception:
        return []
    if not rows or rows[0].get("name") == "No results returned":
        return []
    cats = TV_CATS if mode == "tv" else MOVIE_CATS
    out = []
    seen = set()
    for r in rows:
        if r.get("category") not in cats:
            continue
        name = r.get("name") or ""
        if mode == "tv":
            ep = extract_episode(name)
            title = clean_title(name)
        else:
            if re.search(r"\bS\d{1,2}E\d{1,2}\b", name, re.I):
                continue
            ep = ""
            title = clean_title(name)
            if not title:
                title = re.sub(r"\s*[-–—]+\s*", " ", name).strip()
        year = extract_year(name)
        key = (title, year, _quality(name))
        if key in seen:
            continue
        seen.add(key)
        info_hash = (r.get("info_hash") or "").lower()
        if not re.fullmatch(r"[0-9a-f]{40}", info_hash):
            continue
        out.append({
            "source": "tpb",
            "title": title,
            "year": year,
            "quality": _quality(name),
            "size": human_size(r.get("size")),
            "info_hash": info_hash,
            "seeders": r.get("seeders") or 0,
            "extra_info": ep,
            "score": 0,
            "magnet": None,
            "raw": name,
        })
    return out


def search(query, net, mode="movie", lang=None, quality=None):
    q = urllib.parse.quote(query)
    urls = [f"{base}/q.php?q={q}&cat=0" for base in MIRRORS]
    datas = net.parallel_get(urls, sources=["tpb"] * len(urls))
    for base, url in zip(MIRRORS, urls):
        data = datas[url]
        if not data:
            continue
        out = _parse(data, mode)
        if out:
            return out
    return []


def human_size(size):
    try:
        n = int(size)
    except (TypeError, ValueError):
        return "?"
    if n <= 0:
        return "?"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{int(n)} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"
