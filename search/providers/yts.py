import json
import re
import urllib.parse

from utils.misc import clean_title, extract_year, sanitize_field

MIRRORS = ["yts.mx", "yts.rs", "yts.lt"]

API_URL = "https://{m}/api/v2/list_movies.json?query_term={q}&limit=50&sort_by=seeds"
BROWSE_URL = "https://{m}/browse-movies/{q}"

SOURCE_BONUS = None


def _from_api(data):
    out = []
    try:
        movies = json.loads(data).get("data", {}).get("movies") or []
    except Exception:
        return out
    for mv in movies:
        title = clean_title(mv.get("title") or "")
        year = mv.get("year") or 0
        rating = mv.get("rating") or ""
        for tr in mv.get("torrents") or []:
            quality = (tr.get("quality") or "").lower()
            if quality in ("", "3d"):
                continue
            out.append({
                "source": "yts",
                "title": title,
                "year": year,
                "quality": quality,
                "size": tr.get("size") or "?",
                "info_hash": (tr.get("hash") or "").lower(),
                "seeders": tr.get("seeds") or 0,
                "extra_info": f"IMDB {rating}" if rating else "",
                "score": 0,
                "magnet": None,
                "raw": title,
            })
    return out


def _from_browse(data):
    out = []
    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        data,
        re.DOTALL,
    )
    if not m:
        return out
    try:
        payload = json.loads(m.group(1))
        movies = payload.get("props", {}).get("pageProps", {}).get("movies", [])
    except Exception:
        return out
    for mv in movies:
        title = clean_title(mv.get("title") or "")
        year = mv.get("year") or 0
        rating = mv.get("rating") or ""
        for tr in mv.get("torrents") or []:
            quality = (tr.get("quality") or "").lower()
            if quality in ("", "3d"):
                continue
            out.append({
                "source": "yts",
                "title": title,
                "year": year,
                "quality": quality,
                "size": tr.get("size") or "?",
                "info_hash": (tr.get("hash") or "").lower(),
                "seeders": tr.get("seeds") or 0,
                "extra_info": f"IMDB {rating}" if rating else "",
                "score": 0,
                "magnet": None,
            })
    return out


def search(query, net, mode="movie", lang=None, quality=None):
    if mode != "movie":
        return []
    q = urllib.parse.quote(query)
    urls = [API_URL.format(m=m, q=q) for m in MIRRORS]
    datas = net.parallel_get(urls, sources=["yts"] * len(urls))
    for m, url in zip(MIRRORS, urls):
        data = datas[url]
        if data:
            out = _from_api(data)
            if out:
                return out
    urls = [BROWSE_URL.format(m=m, q=q) for m in MIRRORS]
    datas = net.parallel_get(urls, sources=["yts"] * len(urls))
    for m, url in zip(MIRRORS, urls):
        data = datas[url]
        if data:
            out = _from_browse(data)
            if out:
                return out
    return []
