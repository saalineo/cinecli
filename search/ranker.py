import difflib
import math

from utils.misc import quality_rank

SOURCE_WEIGHT = {
    "yts": 1.0,
    "eztv": 1.0,
    "solid": 0.95,
    "nyaa": 0.9,
    "tpb": 0.9,
    "x1337": 0.9,
    "lime": 0.8,
    "galaxy": 0.8,
    "btdig": 0.7,
}


def rank(results, query, quality=None):
    qnorm = re_norm(query)
    for r in results:
        title = r.get("title", "") or ""
        seeds = int(r.get("seeders") or 0)
        ratio = difflib.SequenceMatcher(None, qnorm, re_norm(title)).ratio()
        seed_factor = 1 + math.log10(seeds + 1)
        quality_factor = 0.4 + 0.2 * quality_rank(r.get("quality"))
        source_factor = SOURCE_WEIGHT.get(r.get("source"), 0.7)
        pref = 15 if quality and r.get("quality") == quality else 0
        score = seed_factor * quality_factor * source_factor * 10 + ratio * 10 + pref
        r["score"] = round(score, 2)
    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return results


def re_norm(text):
    import re

    return re.sub(r"[^a-z0-9 ]", " ", (text or "").lower()).strip()
