import re

TRAILING_TAG_RE = re.compile(
    r"\b(?:bonus|hybrid|multi|extras?|special|collector\'?s?|limited|director\'?s?|cut|remux|unrated)\b$",
    re.I,
)


def norm_title(text):
    t = re.sub(r"[^a-z0-9 ]", " ", (text or "").lower())
    return re.sub(r"\s+", " ", t).strip()


def strip_trailing(title, year):
    t = (title or "").strip()
    while True:
        if year:
            t = re.sub(rf"\s+{re.escape(str(year))}$", "", t)
        nt = TRAILING_TAG_RE.sub("", t).strip()
        if nt == t:
            break
        t = nt
    return t


def dedupe(results):
    by_hash = {}
    for r in results:
        r = dict(r)
        r["title"] = strip_trailing(r.get("title", ""), r.get("year") or 0)
        info_hash = (r.get("info_hash") or "").lower()
        if info_hash:
            existing = by_hash.get(info_hash)
            if existing is None or int(r.get("seeders") or 0) > int(existing.get("seeders") or 0):
                by_hash[info_hash] = r
        else:
            by_hash.setdefault("__nohash_" + _key(r)[0] + _key(r)[1] + _key(r)[2], r)

    merged = {}
    for r in by_hash.values():
        key = _key(r)
        existing = merged.get(key)
        if existing is None or int(r.get("seeders") or 0) > int(existing.get("seeders") or 0):
            merged[key] = r
    return list(merged.values())


def _key(r):
    return (norm_title(r.get("title", "")), str(r.get("year", 0)), str(r.get("quality", "unknown")))
