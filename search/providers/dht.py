import re
import urllib.parse

from utils.misc import clean_title, extract_year, extract_episode, infohash_from_magnet, sanitize_field

MIRRORS = ["https://btdig.com", "https://btsearch.ml"]

RESULT_RE = re.compile(
    r"<div[^>]*class=\"search-result-titles\"[^>]*>\s*<a[^>]*href=\"([^\"]+)\"[^>]*>([^<]+)</a>"
    r".*?href=\"(magnet:\?xt=urn:btih:[0-9a-fA-F]{40}[^\"]*)\"",
    re.DOTALL | re.I,
)


def search(query, net, mode="movie", lang=None, quality=None):
    q = urllib.parse.quote(query)
    urls = [f"{base}/search?q={q}" for base in MIRRORS]
    datas = net.parallel_get(urls, sources=["btdig"] * len(urls))
    out = []
    for base, url in zip(MIRRORS, urls):
        data = datas[url]
        if not data:
            continue
        rows = RESULT_RE.findall(data)
        if not rows:
            continue
        for link, name, magnet in rows[:20]:
            info_hash = infohash_from_magnet(magnet)
            if not info_hash:
                continue
            title = clean_title(name)
            if not title:
                continue
            out.append({
                "source": "btdig",
                "title": title,
                "year": extract_year(name),
                "quality": _quality(name),
                "size": "?",
                "info_hash": info_hash,
                "seeders": 0,
                "extra_info": extract_episode(name),
                "score": 0,
                "magnet": magnet,
                "raw": name,
            })
        if out:
            return out
    return []


def _quality(name):
    m = re.search(r"\b(2160|1080|720|480)p\b", name or "", re.I)
    return m.group(0).lower() if m else "unknown"
