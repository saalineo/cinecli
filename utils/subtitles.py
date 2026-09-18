import io
import json
import os
import re
import urllib.parse
import urllib.request
import zipfile

from utils.misc import clean_title, extract_year

SUBDL_API = "https://api.subdl.com/api/v1/subtitles"

LANG_MAP = {
    "english": "en",
    "hindi": "hi",
    "tamil": "ta",
    "telugu": "te",
    "malayalam": "ml",
    "kannada": "kn",
    "bengali": "bn",
    "spanish": "es",
    "french": "fr",
    "german": "de",
    "japanese": "ja",
    "korean": "ko",
    "chinese": "zh",
    "russian": "ru",
    "arabic": "ar",
    "portuguese": "pt",
    "italian": "it",
    "turkish": "tr",
    "polish": "pl",
    "dutch": "nl",
}


def fetch_subtitles(title, year=None, lang="en", outdir="/tmp"):
    if not title:
        return None

    lang_code = LANG_MAP.get((lang or "en").lower(), lang or "en")
    parsed_year = year or extract_year(title)
    search_title = clean_title(title) if parsed_year else title

    params = {
        "film_name": search_title or title,
        "languages": lang_code,
        "type": "movie",
    }
    if parsed_year:
        params["film_year"] = str(parsed_year)

    url = f"{SUBDL_API}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "cinecli/2.0"})

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

    if not data.get("status") or not data.get("subtitles"):
        if "film_year" in params:
            params_no_year = dict(params)
            del params_no_year["film_year"]
            url_no_year = f"{SUBDL_API}?{urllib.parse.urlencode(params_no_year)}"
            req_no_year = urllib.request.Request(url_no_year, headers={"User-Agent": "cinecli/2.0"})
            try:
                with urllib.request.urlopen(req_no_year, timeout=10) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
            except Exception:
                return None

        if not data.get("status") or not data.get("subtitles"):
            return None

    # Pick first matching result
    sub = data["subtitles"][0]
    sub_url = f"https://dl.subdl.com{sub.get('url')}"

    try:
        sub_req = urllib.request.Request(sub_url, headers={"User-Agent": "cinecli/2.0"})
        with urllib.request.urlopen(sub_req, timeout=10) as resp:
            content = resp.read()

        os.makedirs(outdir, exist_ok=True)
        safe_base = re.sub(r"[^\w\-.]", "_", title).strip("_")
        sub_path = os.path.join(outdir, f"{safe_base}_{lang_code}.srt")

        # Handle zip or direct srt
        if sub_url.endswith(".zip") or content.startswith(b"PK"):
            with zipfile.ZipFile(io.BytesIO(content)) as z:
                for name in z.namelist():
                    if name.lower().endswith(".srt"):
                        with open(sub_path, "wb") as f:
                            f.write(z.read(name))
                        return os.path.abspath(sub_path)
        else:
            with open(sub_path, "wb") as f:
                f.write(content)
            return os.path.abspath(sub_path)
    except Exception:
        return None
    return None
