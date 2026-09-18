import os
import time
import urllib.request
from pathlib import Path

TRACKER_BEST_URL = "https://raw.githubusercontent.com/ngosang/trackerslist/master/trackers_best.txt"
CACHE_DIR = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache"))) / "cinecli"
CACHE_FILE = CACHE_DIR / "trackers.txt"
CACHE_TTL = 86400


def _read_cache():
    if not CACHE_FILE.exists():
        return None
    try:
        lines = CACHE_FILE.read_text(encoding="utf-8").splitlines()
        trackers = [line.strip() for line in lines if line.strip() and not line.startswith("#")]
        return trackers if trackers else None
    except Exception:
        return None


def _write_cache(trackers):
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text("\n".join(trackers) + "\n", encoding="utf-8")
    except Exception:
        pass


def _fetch_remote(timeout=3):
    req = urllib.request.Request(
        TRACKER_BEST_URL,
        headers={"User-Agent": "cinecli/2.0"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        content = resp.read().decode("utf-8", errors="ignore")
        lines = content.splitlines()
        trackers = [line.strip() for line in lines if line.strip() and not line.startswith("#")]
        return trackers if trackers else None


def get_live_trackers(fallback=None, timeout=3):
    if CACHE_FILE.exists():
        try:
            mtime = CACHE_FILE.stat().st_mtime
            if (time.time() - mtime) < CACHE_TTL:
                cached = _read_cache()
                if cached:
                    return cached
        except Exception:
            pass

    try:
        fresh = _fetch_remote(timeout=timeout)
        if fresh:
            _write_cache(fresh)
            return fresh
    except Exception:
        pass

    cached = _read_cache()
    if cached:
        return cached

    return fallback or []


if __name__ == "__main__":
    live = get_live_trackers()
    for tr in live:
        print(tr)
