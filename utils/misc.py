import re
import urllib.parse

QUALITY_RE = (
    r"\b(?:2160|1080|720|480|360)[pP]\b"
    r"|\b4k\b"
    r"|\b(?:x|h)\.?26[45]\b"
    r"|\b(?:mp4|mkv|avi|webm|m4v)\b"
    r"|\b(?:hdr|hdr10|dv|dolby\.?vision|atmos|truehd|dts(?:-hd(?:\.?ma)?)?|ddp?5\.1|aac(?:-he)?|ac3|eac3)\b"
    r"|\b(?:bluray|web-?dl|web-?rip|hdtv|hdrip|brrip|bdrip|remux|dvdr)\b"
    r"|\b(?:amzn|atvp|apple|itunes|netflix|nf|hulu|hbomax)\b"
)

EPISODE_RE = re.compile(r"\bS\d{1,2}E\d{1,2}(?:[-Ee]?\d{1,2})?\b", re.I)
YEAR_RE = re.compile(r"\b((?:19|20)\d{2})\b")
SIZE_RE = re.compile(r"([\d.]+)\s*([KMGT]?i?B)", re.I)
RES_RE = re.compile(r"\b(2160|1080|720|480|360)[pP]\b|\b4k\b", re.I)

SIZE_UNITS = {"B": 1, "KB": 1024, "KIB": 1024, "MB": 1024 ** 2, "MIB": 1024 ** 2,
              "GB": 1024 ** 3, "GIB": 1024 ** 3, "TB": 1024 ** 4, "TIB": 1024 ** 4}

QUALITY_RANK = {"2160p": 4, "1080p": 3, "720p": 2, "480p": 1, "unknown": 0}


def infohash_from_magnet(magnet):
    m = re.search(r"btih:([0-9a-fA-F]{40})", magnet or "")
    return m.group(1).lower() if m else None


def magnet_for(infohash, title="", trackers=None):
    parts = [f"magnet:?xt=urn:btih:{infohash}"]
    if title:
        parts.append("dn=" + urllib.parse.quote(title or ""))
    for tr in trackers or []:
        parts.append("tr=" + urllib.parse.quote(str(tr), safe=""))
    return "&".join(parts)


def parse_size(text):
    m = SIZE_RE.search(text or "")
    if not m:
        return 0
    unit = m.group(2).upper()
    return int(float(m.group(1)) * SIZE_UNITS.get(unit, 1))


def human_size(num):
    try:
        n = float(num)
    except (TypeError, ValueError):
        return "?"
    if n <= 0:
        return "?"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{int(n)} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def quality_of(title):
    m = RES_RE.search(title or "")
    if not m:
        return "unknown"
    q = m.group(0).lower()
    if q == "4k":
        return "2160p"
    return q if q.endswith("p") else q + "p"


def quality_rank(quality):
    return QUALITY_RANK.get(quality, 0)


def clean_title(name):
    n = re.sub(r"[\(\[].*?[\)\]]", " ", name or "")
    m = re.search(QUALITY_RE, n, re.I)
    if m:
        n = n[: m.start()]
    n = re.sub(r"[._]", " ", n)
    n = re.sub(r"\s*[-–—]+\s*", " ", n)
    n = re.sub(
        r"\b(?:proper|repack|extended|internal|remux|complete|dual[- ]?audio|multi[- ]?audio)\b",
        " ",
        n,
        flags=re.I,
    )
    n = re.sub(r"\s+", " ", n).strip()
    return n


def extract_year(name):
    m = YEAR_RE.search(name or "")
    return int(m.group(1)) if m else 0


def extract_episode(name):
    m = EPISODE_RE.search(name or "")
    return m.group(0).upper() if m else ""


def sanitize_field(text):
    return re.sub(r"[|]", "-", text or "").strip()


def video_ext(name):
    m = re.search(r"\.(mp4|mkv|webm|avi|mov|m4v)$", name or "", re.I)
    return m.group(1).lower() if m else None
