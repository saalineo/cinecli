import re
import urllib.parse

from utils.misc import clean_title, extract_year, extract_episode, infohash_from_magnet, sanitize_field

MIRRORS = ["https://www.limetorrents.lol", "https://www.limetorrents.info"]

ROW_RE = re.compile(
    r"<div[^>]*class=\"(?:name|t-name)\"[^>]*>\s*<a[^>]*href=\"([^\"]+)\"[^>]*>([^<]+)</a>"
    r".*?class=\"tdnormal\"[^>]*>\s*([\d.,]+\s*[KMGT]i?B)",
    re.DOTALL | re.I,
)

MAGNET_RE = re.compile(r'href="(magnet:\?xt=urn:btih:[0-9a-fA-F]{40}[^"]*)"', re.I)


def search(query, net, mode="movie", lang=None, quality=None):
    q = urllib.parse.quote(query)
    urls = [f"{base}/search/all/{q}/" for base in MIRRORS]
    datas = net.parallel_get(urls, sources=["lime"] * len(urls))
    rows = []
    base = None
    for candidate, url in zip(MIRRORS, urls):
        data = datas[url]
        if not data:
            continue
        found = ROW_RE.findall(data)
        if found:
            rows, base = found, candidate
            break
    if not rows or not base:
        return []
    out = []
    for link, name, size in rows[:4]:
        magnet = None
        detail = net.get(base + link, source="lime")
        if detail:
            mm = MAGNET_RE.search(detail)
            if mm:
                magnet = mm.group(1)
        info_hash = infohash_from_magnet(magnet)
        if not info_hash:
            continue
        title = clean_title(name)
        if re.search(r"\bS\d{1,2}E\d{1,2}\b", name, re.I) and mode == "movie":
            continue
        out.append({
            "source": "lime",
            "title": title,
            "year": extract_year(name),
            "quality": _quality(name),
            "size": size.strip(),
            "info_hash": info_hash,
            "seeders": 0,
            "extra_info": extract_episode(name),
            "score": 0,
            "magnet": magnet,
            "raw": name,
        })
    return out


def _quality(name):
    m = re.search(r"\b(2160|1080|720|480)p\b", name or "", re.I)
    return m.group(0).lower() if m else "unknown"
