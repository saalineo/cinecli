import re
import urllib.parse
import xml.etree.ElementTree as ET

from utils.misc import clean_title, extract_year, extract_episode, infohash_from_magnet, sanitize_field

BASE = "https://nyaa.si"

try:
    import feedparser
except Exception:
    feedparser = None

NS = {
    "nyaa": "https://nyaa.si/xmlns/nyaa",
    "atom": "http://www.w3.org/2005/Atom",
    "dc": "http://purl.org/dc/elements/1.1/",
}


def _parse_rss(data):
    out = []
    if feedparser is not None:
        feed = feedparser.parse(data)
        for e in feed.entries:
            magnet = e.get("link") or ""
            info_hash = infohash_from_magnet(magnet)
            if not info_hash:
                guid = e.get("guid") or ""
                info_hash = infohash_from_magnet(guid)
            if not info_hash:
                continue
            name = (e.get("title") or "").strip()
            size = e.get("nyaa_size") or e.get("size") or "?"
            seeders = e.get("nyaa_seeders") or 0
            out.append((name, magnet, size, seeders, info_hash))
        return out
    root = ET.fromstring(data)
    for item in root.iter("item"):
        def _tag(tag):
            el = item.find(tag, NS)
            return el.text.strip() if el is not None and el.text else ""
        magnet = _tag("link")
        info_hash = infohash_from_magnet(magnet) or infohash_from_magnet(_tag("guid"))
        if not info_hash:
            continue
        name = _tag("title")
        seed_el = item.find("nyaa:seeders", NS)
        seeders = int(seed_el.text.strip()) if seed_el is not None and seed_el.text else 0
        size_el = item.find("nyaa:size", NS)
        size = size_el.text.strip() if size_el is not None and size_el.text else "?"
        out.append((name, magnet, size, seeders, info_hash))
    return out


def search(query, net, mode="movie", lang=None, quality=None):
    q = urllib.parse.quote(query)
    url = f"{BASE}/?page=rss&c=0_0&q={q}"
    data = net.get(url, source="nyaa")
    if not data:
        return []
    try:
        entries = _parse_rss(data)
    except Exception:
        return []
    out = []
    for name, magnet, size, seeders, info_hash in entries:
        title = clean_title(name)
        if not title:
            continue
        out.append({
            "source": "nyaa",
            "title": title,
            "year": extract_year(name),
            "quality": _quality(name),
            "size": size,
            "info_hash": info_hash,
            "seeders": seeders,
            "extra_info": extract_episode(name),
            "score": 0,
            "magnet": magnet,
            "raw": name,
        })
    return out


def _quality(name):
    m = re.search(r"\b(2160|1080|720|480)p\b", name or "", re.I)
    return m.group(0).lower() if m else "unknown"
