import re

LANGUAGES = {
    "english": [r"english", r"\beng\b", r"\(en\)", r"\[en\]", r"multi[- ]?audio", r"dual[- ]?audio", r"multisub"],
    "hindi": [r"hindi", r"bollywood", r"\bhin\b", r"\(hi\)", r"\[hi\]", r"hindi[- ]dubbed", r"dubbed.*hindi"],
    "tamil": [r"tamil", r"\btam\b", r"kollywood", r"\(ta\)", r"\[ta\]"],
    "telugu": [r"telugu", r"tegu", r"tollywood", r"\btel\b", r"\(te\)"],
    "malayalam": [r"malayalam", r"mollywood", r"\bmal\b", r"\(ml\)"],
    "kannada": [r"kannada", r"sandalwood", r"\bkan\b", r"\(kn\)"],
    "bengali": [r"bengali", r"bangla", r"\bben\b", r"\(bn\)"],
    "spanish": [r"spanish", r"espa[ñn]ol", r"castellano", r"\blat\b", r"latino", r"\bspa\b", r"\(es\)", r"\[es\]"],
    "french": [r"french", r"fran[çc]ais", r"\bfra\b", r"vff", r"vostfr", r"vfq", r"\(fr\)", r"\[fr\]"],
    "german": [r"german", r"deutsch", r"\bger\b", r"\bdeu\b", r"\(de\)", r"\[de\]"],
    "japanese": [r"japanese", r"\bjpn\b", r"\bjap\b", r"japan", r"\(ja\)", r"\[ja\]"],
    "korean": [r"korean", r"\bkor\b", r"kdrama", r"\(ko\)", r"\[ko\]"],
    "chinese": [r"chinese", r"mandarin", r"cantonese", r"\bchi\b", r"\bzho\b", r"\(zh\)", r"\[zh\]"],
    "russian": [r"russian", r"russkij", r"\brus\b", r"\(ru\)", r"\[ru\]"],
    "arabic": [r"arabic", r"\bara\b", r"\(ar\)", r"\[ar\]"],
    "portuguese": [r"portuguese", r"portugu[eê]s", r"\bpor\b", r"\bpt[- ]br\b", r"\(pt\)", r"\[pt\]"],
    "italian": [r"italian", r"italiano", r"\bita\b", r"\(it\)", r"\[it\]"],
    "turkish": [r"turkish", r"t[uü]rk[çc]e", r"\btur\b", r"\(tr\)", r"\[tr\]"],
    "polish": [r"polish", r"polski", r"\bpol\b", r"\(pl\)", r"\[pl\]"],
    "dutch": [r"dutch", r"nederlands", r"\bdut\b", r"\bnl\b", r"\(nl\)", r"\[nl\]"],
}

ALIASES = {
    "hindi": ["hindi", "bollywood", "hi", "hin"],
    "tamil": ["tamil", "tam", "ta"],
    "telugu": ["telugu", "tel", "te"],
    "malayalam": ["malayalam", "mal", "ml"],
    "kannada": ["kannada", "kan", "kn"],
    "bengali": ["bengali", "ben", "bn"],
    "spanish": ["spanish", "espanol", "espa", "lat", "es"],
    "french": ["french", "francais", "fra", "fr"],
    "german": ["german", "deutsch", "ger", "de"],
    "japanese": ["japanese", "jpn", "jap", "ja"],
    "korean": ["korean", "kor", "ko"],
    "chinese": ["chinese", "mandarin", "chi", "zho", "zh"],
    "russian": ["russian", "rus", "ru"],
    "arabic": ["arabic", "ara", "ar"],
    "portuguese": ["portuguese", "portugues", "por", "pt"],
    "italian": ["italian", "ita", "it"],
    "turkish": ["turkish", "tur", "tr"],
    "polish": ["polish", "pol", "pl"],
    "dutch": ["dutch", "dut", "nl"],
    "english": ["english", "eng", "en"],
}

DUAL_RE = re.compile(r"dual[- ]?audio|multi[- ]?audio|multisub|dubbed", re.I)

_COMPILED = {lang: [re.compile(p, re.I) for p in patterns] for lang, patterns in LANGUAGES.items()}


def detect(title):
    low = title or ""
    hits = []
    for lang, patterns in _COMPILED.items():
        for p in patterns:
            if p.search(low):
                hits.append(lang)
                break
    return hits


def is_dual(title):
    return bool(DUAL_RE.search(title or ""))


def matches(title, lang):
    if not lang or lang in ("any", "all"):
        return True
    key = lang.lower()
    hits = detect(title)
    if key == "english":
        if not hits:
            return True
        if is_dual(title):
            return True
        return "english" in hits
    return key in hits


def canonical_lang(name):
    name = (name or "").lower()
    if name in ALIASES:
        return name
    for lang, aliases in ALIASES.items():
        if name in aliases:
            return lang
    for lang, aliases in ALIASES.items():
        for alias in aliases:
            if alias in name:
                return lang
    return name
