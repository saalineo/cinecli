import multiprocessing
import queue
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
    # Do not mutate configuration or re-enable sources a user deliberately
    # disabled.  Language affects the query and ranking, never consent.
    src = dict(cfg.get("sources") or {})
    order = list(PROVIDER_ORDER)
    if mode == "movie":
        order.remove("eztv")

    def _is_enabled(name):
        # Direct key takes precedence; PROVIDER_ORDER uses "dht" but config uses "btdig"
        if name in src:
            return bool(src[name])
        if name == "dht" and "btdig" in src:
            return bool(src["btdig"])
        return True

    return [name for name in order if _is_enabled(name)]


def _run_provider(module_name, query, mode, lang, quality, net):
    try:
        mod = providers.get(module_name)
        results = mod.search(query, net=net, mode=mode, lang=lang, quality=quality)
        return module_name, list(results)
    except Exception:
        return module_name, []


def _provider_worker(result_queue, module_name, query, mode, lang, quality, net):
    """Run one untrusted/brittle provider in an isolated process.

    A thread cannot be safely cancelled while blocked in a network operation;
    a process can. Provider failures are already converted to an empty result.
    """
    try:
        result_queue.put(_run_provider(module_name, query, mode, lang, quality, net))
    except Exception:
        result_queue.put((module_name, []))


def search(query, mode="movie", lang=None, quality=None, max_results=50, cfg=None, net=None, progress=None):
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
    request_timeout = max(1, min(int(cfg.get("timeout", 30)), 8))
    net = net or Net(
        timeout=request_timeout,
        proxy=cfg.get("http_proxy") or cfg.get("proxy"),
        use_doh=cfg.get("use_doh", True),
    )

    sources = enabled_sources(cfg, mode, lang)
    results = []
    status = {}
    dropped = 0
    budget = max(1.0, float(cfg.get("search_budget", SEARCH_BUDGET)))
    # cinecli supports POSIX platforms. ``fork`` lets the child inherit the
    # prepared network object and, importantly, lets the parent terminate a
    # provider that ignores a timeout or hangs in a third-party scraper.
    context = multiprocessing.get_context("fork")
    result_queue = context.Queue()
    workers = []

    def emit(source, state, count=None):
        if progress:
            try:
                progress(source, state, count)
            except Exception:
                pass

    try:
        for name in sources:
            worker = context.Process(
                target=_provider_worker,
                args=(result_queue, name, provider_query, mode, lang, quality, net),
                daemon=True,
            )
            worker.start()
            workers.append(worker)
            emit(name, "searching")

        pending = set(sources)
        deadline = time.monotonic() + budget
        while pending:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                name, res = result_queue.get(timeout=remaining)
            except queue.Empty:
                break
            if name not in pending:
                continue
            pending.remove(name)
            results.extend(res)
            status[name] = len(res)
            emit(name, "complete", len(res))
        dropped = len(pending)
        for name in pending:
            emit(name, "timed out")
    finally:
        for worker in workers:
            if worker.is_alive():
                worker.terminate()
            worker.join(timeout=1)
        result_queue.close()
        result_queue.join_thread()
    if dropped:
        sys.stderr.write(f"  {dropped} slow source(s) skipped after {int(budget)}s\n")

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

    if max_results is not None:
        max_results = int(max_results)
        if max_results <= 0:
            raise ValueError("max_results must be a positive integer")
        results = results[:max_results]

    return results, status, fallback


def res_rank(q):
    return RES_MIN.get(q, 0)
