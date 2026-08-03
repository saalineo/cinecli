import re
import urllib.parse

from utils.misc import clean_title, extract_year, extract_episode, infohash_from_magnet, human_size, sanitize_field

MIRRORS = ["https://zooqle.com"]

ROW_RE = re.compile(
    r"<tr[^>]*>\s*<td[^>]*>\s*<div[^>]*class=\"torrent-name\"[^>]*>.*?<a[^>]*href=\"([^\"]+)\"[^>]*>([^<]+)</a>"
    r".*?<td[^>]*>\s*([\d.,]+\s*[KMGT]i?B)\s*</td>"
    r".*?<td[^>]*>\s*(\d+)\s*</td>",
    re.DOTALL | re.I,
)

MAGNET_RE = re.compile(r'href="(magnet:\?xt=urn:btih:[0-9a-fA-F]{40}[^"]*)"', re.I)


def search(query, net, mode="movie", lang=None, quality=None):
    q = urllib.parse.quote(query)
    urls = [f"{base}/search?q={q}" for base in MIRRORS]
    datas = net.parallel_get(urls, sources=["zooqle"] * len(urls))
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
    for link, name, size, seeds in rows[:4]:
        magnet = None
        detail = net.get(base + link, source="zooqle")
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
            "source": "zooqle",
            "title": title,
            "year": extract_year(name),
            "quality": _quality(name),
            "size": size.strip(),
            "info_hash": info_hash,
            "seeders": _int(seeds),
            "extra_info": extract_episode(name),
            "score": 0,
            "magnet": magnet,
            "raw": name,
        })
    return out


def _quality(name):
    m = re.search(r"\b(2160|1080|720|480)p\b", name or "", re.I)
    return m.group(0).lower() if m else "unknown"


def _int(text):
    m = re.search(r"\d+", text or "")
    return int(m.group(0)) if m else 0
