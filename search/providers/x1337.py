import re
import urllib.parse

from utils.misc import clean_title, extract_year, extract_episode, infohash_from_magnet

MIRRORS = [
    "https://1337x.to",
    "https://1337x.st",
    "https://1337x.ws",
    "https://1337x.eu",
    "https://1337x.so",
]

try:
    import cloudscraper  # type: ignore
except Exception:
    cloudscraper = None  # type: ignore

try:
    from bs4 import BeautifulSoup  # type: ignore
except Exception:
    BeautifulSoup = None  # type: ignore

_scraper = None


def _scrape(net, url):
    if cloudscraper is not None:
        global _scraper
        if _scraper is None:
            try:
                _scraper = cloudscraper.create_scraper()
            except Exception:
                _scraper = None
        if _scraper is not None:
            try:
                resp = _scraper.get(url, timeout=net.timeout)
                # cloudscraper returns Response with .text
                text = getattr(resp, "text", None)
                if text:
                    return text
            except Exception:
                pass
            # Fall through to net.get on cloudscraper failure/empty
    return net.get(url, source="x1337")


def _quality(name):
    m = re.search(r"\b(2160|1080|720|480)p\b", name or "", re.I)
    return m.group(0).lower() if m else "unknown"


def search(query, net, mode="movie", lang=None, quality=None):
    if not query or not net:
        return []
    category = "Movies" if mode == "movie" else "TV"
    q = urllib.parse.quote(query)

    html = None
    chosen_mirror = None
    for mirror in MIRRORS:
        url = f"{mirror}/category-search/{q}/{category}/1/"
        html = _scrape(net, url)
        if html and "table-list" in html:
            chosen_mirror = mirror
            break

    if not html or not chosen_mirror:
        return []

    # Prefer BeautifulSoup parsing as per current 1337x structure.
    # Fallback to regex if BeautifulSoup unavailable (e.g., venv without bs4).
    rows = []
    if BeautifulSoup is not None:
        soup = BeautifulSoup(html, "html.parser")
        rows = soup.select("table.table-list tbody tr")
    else:
        # Minimal regex fallback matching old spec's table-list rows
        # Extract href, name, seeds, size col-like patterns
        pat = re.compile(
            r'<tr.*?<td[^>]*class="[^"]*name[^"]*"[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>([^<]+)</a>'
            r'.*?<td[^>]*class="[^"]*seeds[^"]*"[^>]*>([^<]*)</td>'
            r'.*?<td[^>]*class="[^"]*size[^"]*"[^>]*>([^<]*)</td>',
            re.DOTALL | re.I,
        )
        # Build pseudo-rows as objects with helper accessors
        class _R:
            def __init__(self, href, name, seeds, size):
                self.href = href
                self.name = name
                self.seeds = seeds
                self.size = size
        for m in pat.finditer(html):
            rows.append(_R(m.group(1), m.group(2), m.group(3), m.group(4)))
        # If fallback found nothing, treat as no results
        if not rows:
            return []

    results = []
    for row in rows:
        # Bound detail-page fetches to avoid unbounded external calls.
        if len(results) >= 6:
            break

        if BeautifulSoup is not None:
            name_elem = row.select_one("td.name a:nth-of-type(2)")
            if not name_elem:
                continue
            detail_path = name_elem.get("href", "")
            name = name_elem.get_text(strip=True)
            seeders_elem = row.select_one("td.seeds")
            size_elem = row.select_one("td.size")
            seeders_raw = seeders_elem.get_text(strip=True) if seeders_elem else "0"
            m_seed = re.search(r"[\d,]+", seeders_raw or "")
            seeders = int(m_seed.group(0).replace(",", "")) if m_seed else 0
            size_raw = size_elem.get_text(strip=True) if size_elem else ""
            size_str = size_raw.strip()
        else:
            # regex fallback object
            detail_path = row.href  # type: ignore
            name = row.name  # type: ignore
            seeders_raw = row.seeds  # type: ignore
            m = re.search(r"\d+", seeders_raw or "")
            seeders = int(m.group(0)) if m else 0
            size_str = (row.size or "").strip()  # type: ignore

        if not name or not detail_path:
            continue

        # Validate detail path to prevent SSRF via crafted href (e.g., //evil.com or http://)
        if not detail_path.startswith("/torrent/"):
            continue

        # Skip TV episodes when searching movies (preserve prior behavior)
        if mode == "movie" and re.search(r"\bS\d{1,2}E\d{1,2}\b", name, re.I):
            continue

        detail_url = urllib.parse.urljoin(chosen_mirror, detail_path)
        detail_html = _scrape(net, detail_url)
        if not detail_html:
            continue

        magnet_match = re.search(r'href="(magnet:\?xt=urn:btih:[a-zA-Z0-9]+[^"]*)"', detail_html, re.I)
        if not magnet_match:
            continue

        magnet = magnet_match.group(1)
        info_hash = infohash_from_magnet(magnet)
        if not info_hash:
            continue

        results.append({
            "source": "x1337",
            "title": clean_title(name),
            "year": extract_year(name),
            "quality": _quality(name),
            "size": size_str,
            "info_hash": info_hash,
            "seeders": seeders,
            "extra_info": extract_episode(name),
            "score": 0,
            "magnet": magnet,
            "raw": name,
        })

    return results
