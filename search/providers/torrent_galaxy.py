import re
import urllib.parse

from utils.misc import clean_title, extract_year, extract_episode, infohash_from_magnet, human_size, sanitize_field

MIRRORS = ["https://torrentgalaxy.to", "https://torrentgalaxy.one"]

ROW_RE = re.compile(
    r"<div[^>]*class=\"t-name\"[^>]*>\s*<a href=\"([^\"]+)\"[^>]*>([^<]+)</a>"
    r"|<div[^>]*class=\"t-size\"[^>]*>\s*([^<]+)",
    re.DOTALL | re.I,
)

MAGNET_RE = re.compile(r'href="(magnet:\?xt=urn:btih:[0-9a-fA-F]{40}[^"]*)"', re.I)


def _parse_list(data):
    entries = []
    current = None
    for m in re.finditer(
        r"<div[^>]*class=\"t-name\"[^>]*>\s*<a href=\"([^\"]+)\"[^>]*>([^<]+)</a>.*?<div[^>]*class=\"t-size\"[^>]*>\s*([^<]+).*?<div[^>]*class=\"t-seed\"[^>]*>\s*<b>([^<]+)</b>.*?<div[^>]*class=\"t-leech\"[^>]*>\s*<b>([^<]+)</b>",
        data,
        re.DOTALL | re.I,
    ):
        entries.append({
            "link": m.group(1),
            "name": m.group(2).strip(),
            "size": m.group(3).strip(),
            "seeders": _int(m.group(4)),
            "leechers": _int(m.group(5)),
        })
    return entries


def search(query, net, mode="movie", lang=None, quality=None):
    q = urllib.parse.quote(query)
    urls = [f"{base}/torrents.php?search={q}#results" for base in MIRRORS]
    datas = net.parallel_get(urls, sources=["galaxy"] * len(urls))
    rows = []
    base = None
    for candidate, url in zip(MIRRORS, urls):
        data = datas[url]
        if not data:
            continue
        found = _parse_list(data)
        if found:
            rows, base = found, candidate
            break
    if not rows or not base:
        return []
    out = []
    for item in rows[:4]:
        magnet = None
        detail = net.get(base + item["link"], source="galaxy")
        if detail:
            mm = MAGNET_RE.search(detail)
            if mm:
                magnet = mm.group(1)
        info_hash = infohash_from_magnet(magnet)
        if not info_hash:
            continue
        name = item["name"]
        title = clean_title(name)
        if re.search(r"\bS\d{1,2}E\d{1,2}\b", name, re.I) and mode == "movie":
            continue
        out.append({
            "source": "galaxy",
            "title": title,
            "year": extract_year(name),
            "quality": _quality(name),
            "size": item["size"],
            "info_hash": info_hash,
            "seeders": item["seeders"],
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
