import re
import urllib.parse

from utils.misc import clean_title, extract_year, extract_episode, infohash_from_magnet, human_size, sanitize_field

MIRRORS = ["https://1337x.to", "https://1337x.st", "https://1337x.is"]

ROW_RE = re.compile(
    r"<tr>\s*<td[^>]*colspan[^>]*>\s*<a href=\"(/torrent/(\d+)/[^\"]+)\">([^<]+)</a>"
    r".*?<td[^>]*class=\"coll-2\"[^>]*>([^<]+)</td>"
    r".*?<td[^>]*class=\"coll-3\"[^>]*>([^<]+)</td>"
    r".*?<td[^>]*class=\"coll-4\"[^>]*>([^<]+)</td>",
    re.DOTALL | re.I,
)

MAGNET_RE = re.compile(r'href="(magnet:\?xt=urn:btih:[0-9a-fA-F]{40}[^"]*)"', re.I)

try:
    import cloudscraper
except Exception:
    cloudscraper = None

_scraper = None


def _scrape(net, url):
    if cloudscraper is not None:
        global _scraper
        if _scraper is None:
            _scraper = cloudscraper.create_scraper()
        try:
            return _scraper.get(url, timeout=net.timeout).text
        except Exception:
            return None
    return net.get(url, source="x1337")


def _quality(name):
    m = re.search(r"\b(2160|1080|720|480)p\b", name or "", re.I)
    return m.group(0).lower() if m else "unknown"


def search(query, net, mode="movie", lang=None, quality=None):
    q = urllib.parse.quote(query)
    rows = []
    base = None
    if cloudscraper is not None:
        for candidate in MIRRORS:
            data = _scrape(net, f"{candidate}/search/{q}/1/")
            if not data:
                continue
            found = ROW_RE.findall(data)
            if found:
                rows, base = found, candidate
                break
    else:
        urls = [f"{m}/search/{q}/1/" for m in MIRRORS]
        datas = net.parallel_get(urls, sources=["x1337"] * len(urls))
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
    for link, tid, name, size, seeds, leech in rows[:4]:
        if re.search(r"\bS\d{1,2}E\d{1,2}\b", name, re.I) and mode == "movie":
            continue
        magnet = None
        detail = _scrape(net, base + link)
        if detail:
            mm = MAGNET_RE.search(detail)
            if mm:
                magnet = mm.group(1)
        info_hash = infohash_from_magnet(magnet)
        if not info_hash:
            continue
        title = clean_title(name)
        out.append({
            "source": "x1337",
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


def _int(text):
    m = re.search(r"\d+", text or "")
    return int(m.group(0)) if m else 0
