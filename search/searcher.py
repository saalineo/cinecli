import concurrent.futures
import re
import sys
import time

from utils.config import load as load_config
from utils.network import Net
from search.deduplicator import dedupe
from search.language_detector import matches, canonical_lang
from search.ranker import rank
from search import providers

SEARCH_BUDGET = 20.0

PROVIDER_ORDER = [
    "yts",
    "eztv",
    "tpb",
    "x1337",
    "solid",
    "galaxy",
    "nyaa",
    "lime",
    "dht",
]

RES_MIN = {
    "2160p": 2160,
    "1080p": 1080,
    "720p": 720,
    "480p": 480,
}


def split_query_year(query):
    m = re.search(r"\b((?:19|20)\d{2})\b", query)
    if m:
        year = int(m.group(1))
        cleaned = (query[: m.start()] + query[m.end():]).strip()
        return cleaned, year
    return query, None


def enabled_sources(cfg, mode, lang):
    src = cfg.get("sources") or {}
    if lang == "japanese":
        src["nyaa"] = True
    order = list(PROVIDER_ORDER)
    if mode == "movie":
        order.remove("eztv")

    def _is_enabled(name):
        # Direct key takes precedence
        if name in src:
            return bool(src[name])
        # Alias handling: PROVIDER_ORDER uses "dht" but config uses "btdig"
        if name == "dht" and "btdig" in src:
            return bool(src["btdig"])
        if name == "btdig" and "dht" in src:
            return bool(src["dht"])
        return True

    return [name for name in order if _is_enabled(name)]


def _run_provider(module_name, query, mode, lang, quality, net):
    try:
        mod = providers.get(module_name)
        results = mod.search(query, net=net, mode=mode, lang=lang, quality=quality)
        return module_name, list(results)
    except Exception:
        return module_name, []


def search(query, mode="movie", lang=None, quality=None, max_results=50, cfg=None, net=None):
    cfg = cfg or load_config()
    lang = canonical_lang(lang) if lang else None
    if quality:
        quality = str(quality).lower()
        if quality in ("4k", "2160"):
            quality = "2160p"
        elif re.fullmatch(r"\d+", quality or ""):
            quality = quality + "p"

    base_query, query_year = split_query_year(query)
    provider_query = base_query
    if lang and lang != "english":
        provider_query = f"{base_query} {lang}"
    request_timeout = min(int(cfg.get("timeout", 30)), 8)
    net = net or Net(
        timeout=request_timeout,
        proxy=cfg.get("proxy"),
        use_doh=cfg.get("use_doh", True),
    )

    sources = enabled_sources(cfg, mode, lang)
    results = []
    status = {}
    dropped = 0
    deadline = time.monotonic() + SEARCH_BUDGET
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=max(4, len(sources)))
    try:
        futures = {
            executor.submit(_run_provider, name, provider_query, mode, lang, quality, net): name
            for name in sources
        }
        for future in concurrent.futures.as_completed(futures):
            if time.monotonic() > deadline:
                dropped += 1
                continue
            name, res = future.result()
            results.extend(res)
            status[name] = len(res)
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
    if dropped:
        sys.stderr.write(f"  {dropped} slow source(s) skipped after {int(SEARCH_BUDGET)}s\n")

    fallback = False
    if query_year:
        results = [r for r in results if abs(int(r.get("year") or 0) - query_year) <= 1]

    if lang:
        filtered = [r for r in results if matches(r.get("raw") or r.get("title", ""), lang)]
        if not filtered and results:
            fallback = True
            filtered = results
        results = filtered

    results = dedupe(results)
    results = rank(results, base_query, quality)

    if quality:
        min_res = RES_MIN.get(quality)
        if min_res:
            preferred = [r for r in results if (r.get("quality") or "unknown").startswith(quality.split("p")[0]) or res_rank(r.get("quality")) >= min_res]
            if preferred:
                results = preferred
        else:
            preferred = [r for r in results if r.get("quality") == quality]
            if preferred:
                results = preferred

    if max_results:
        results = results[:max_results]

    return results, status, fallback


def res_rank(q):
    return RES_MIN.get(q, 0)
