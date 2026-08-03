import re
import urllib.parse

from utils.misc import clean_title, extract_year, extract_episode, infohash_from_magnet, parse_size, human_size, sanitize_field

MIRRORS = [
    "https://eztv.re",
    "https://eztvx.to",
    "https://eztv.ag",
]

ROW_RE = re.compile(r"<tr[^>]*class=\"forum_header_border[^\"]*\"[^>]*>(.*?)</tr>", re.DOTALL | re.I)


def _parse_row(row):
    name_m = re.search(r"<a[^>]*href=\"([^\"]*torrents/[^\"]+)\"[^>]*>([^<]+)</a>", row, re.I)
    if not name_m:
        return None
    name = name_m.group(2).strip()
    magnet_m = re.search(r'href="(magnet:\?xt=urn:btih:[0-9a-fA-F]{40}[^"]*)"', row, re.I)
    size_m = re.search(r"(\d+(?:\.\d+)?\s*[KMGT]i?B)", row, re.I)
    seeds_m = re.search(
        r'class="[^"]*forum_thread_post_sl[^"]*"[^>]*>\s*(\d+)', row, re.I
    ) or re.search(r"class=\"forum_thread_post_sl\">\s*(\d+)", row, re.I)
    return {
        "name": name,
        "magnet": magnet_m.group(1) if magnet_m else None,
        "size": size_m.group(1) if size_m else "?",
        "seeders": int(seeds_m.group(1)) if seeds_m else 0,
    }


def search(query, net, mode="movie", lang=None, quality=None):
    if mode != "tv":
        return []
    q = urllib.parse.quote(query)
    urls = [f"{base}/search/{q}" for base in MIRRORS]
    datas = net.parallel_get(urls, sources=["eztv"] * len(urls))
    out = []
    for base, url in zip(MIRRORS, urls):
        data = datas[url]
        if not data:
            continue
        seen = set()
        for row in ROW_RE.findall(data):
            item = _parse_row(row)
            if not item:
                continue
            title = clean_title(item["name"])
            if not title or title in seen:
                continue
            seen.add(title)
            info_hash = infohash_from_magnet(item["magnet"])
            if not info_hash:
                continue
            out.append({
                "source": "eztv",
                "title": title,
                "year": extract_year(item["name"]),
                "quality": _quality(item["name"]),
                "size": item["size"],
                "info_hash": info_hash,
                "seeders": item["seeders"],
                "extra_info": extract_episode(item["name"]),
                "score": 0,
                "magnet": item["magnet"],
                "raw": item["name"],
            })
        if out:
            return out
    return out


def _quality(name):
    m = re.search(r"\b(2160|1080|720|480)p\b", name or "", re.I)
    return m.group(0).lower() if m else "unknown"
