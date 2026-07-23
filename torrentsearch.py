import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0"
DOH = [
    "curl",
    "-sL",
    "--doh-url",
    "https://cloudflare-dns.com/dns-query",
    "--connect-timeout",
    "10",
    "--max-time",
    "25",
    "-A",
    UA,
]


def fetch(url):
    try:
        r = subprocess.run(DOH + [url], capture_output=True, text=True, timeout=30)
        if r.returncode == 0 and r.stdout:
            return r.stdout
    except:
        pass
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        return urllib.request.urlopen(req, timeout=8).read().decode(errors="replace")
    except:
        return None


def get_yts(query):
    for m in ["yts.rs", "yts.am", "yts.lt", "yts.ag"]:
        h = fetch(f"https://{m}/browse-movies/{urllib.parse.quote(query)}")
        if not h:
            continue
        d = re.search(
            r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
            h,
            re.DOTALL,
        )
        if not d:
            continue
        for mv in (
            json.loads(d.group(1))
            .get("props", {})
            .get("pageProps", {})
            .get("movies", [])
        ):
            t, y, s = mv["title"], mv.get("year", ""), mv["slug"]
            for tr in mv.get("torrents", []):
                print(
                    f"yts|{t}|{y}|{s}|{tr['quality']}|{tr['hash']}|{tr['seeds']}|{tr.get('size', '')}"
                )
        return True
    return False


def get_tpb(query):
    d = fetch(f"https://apibay.org/q.php?q={urllib.parse.quote(query)}&cat=0")
    if not d:
        return False
    try:
        data = json.loads(d)
    except:
        return False
    if not data or data[0].get("name") == "No results returned":
        return False
    seen = set()
    for r in data:
        if r.get("category") not in {
            "201",
            "202",
            "203",
            "204",
            "207",
            "209",
            "210",
            "211",
        }:
            continue
        n = r["name"]
        if re.search(r"\bS\d{2}E\d{2}\b", n, re.I):
            continue
        y = re.search(r"\b((?:19|20)\d{2})\b", n)
        q = re.search(r"\b(2160|1080|720|480)[pP]", n)
        d = re.sub(r"\s*[\(\[]?.*?(?:19|20)\d{2}.*?[\)\]]?\s*", " ", n)
        d = re.sub(r"\s*[-–—]+\s*", " ", d).strip()
        k = f"{d}|{y.group(1) if y else '0'}|{q.group(0).lower() if q else 'unknown'}"
        if k in seen:
            continue
        seen.add(k)
        print(
            f"tpb|{d}|{y.group(1) if y else '0'}|{r['info_hash'][:8]}|{q.group(0).lower() if q else 'unknown'}|{r['info_hash']}|{r.get('seeders', '0')}|"
        )
    return len(seen) > 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <query>", file=sys.stderr)
        sys.exit(1)
    if not get_yts(sys.argv[1]) and not get_tpb(sys.argv[1]):
        print(f"no results for '{sys.argv[1]}'", file=sys.stderr)
        sys.exit(1)
