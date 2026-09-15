import copy
import json
import os
import re
from pathlib import Path

try:
    import yaml
except Exception:
    yaml = None

CONFIG_DIR = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "cinecli"
USER_CONFIG = CONFIG_DIR / "config.yml"

DEFAULTS = {
    "default_quality": "1080p",
    "default_language": "english",
    "download_dir": "~/Downloads",
    "max_results": 50,
    "timeout": 30,
    "vpn_required": False,
    "dns_check": False,
    "use_doh": True,
    "proxy": None,
    "player": "mpv",
    "mpv_args": [],
    "trackers": [
        "udp://tracker.opentrackr.org:1337/announce",
        "udp://tracker.torrent.eu.org:451/announce",
        "udp://open.stealth.si:80/announce",
        "udp://tracker.bittor.pw:1337/announce",
        "udp://exodus.desync.com:6969/announce",
        "udp://tracker.tiny-vps.com:6969/announce",
        "udp://retracker.lanta-net.ru:2710/announce",
        "udp://tracker.moeking.me:6969/announce",
        "udp://tracker.altrosky.nl:6969/announce",
        "https://tracker.ubt.nu:443/announce",
    ],
    "sources": {
        "yts": True,
        "eztv": True,
        "tpb": True,
        "x1337": True,
        "solid": True,
        "galaxy": True,
        "nyaa": True,
        "lime": True,
        "btdig": True,
    },
}


def _merge(base, override):
    out = dict(base)
    for key, val in override.items():
        if isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], val)
        else:
            out[key] = val
    return out


def _convert(val):
    low = val.lower()
    if low in ("true", "yes", "on"):
        return True
    if low in ("false", "no", "off"):
        return False
    if low in ("null", "none", "~"):
        return None
    if val.startswith("[") and val.endswith("]"):
        items = [i.strip().strip("\"'") for i in val[1:-1].split(",")]
        return [i for i in items if i]
    if re.fullmatch(r"-?\d+", val):
        return int(val)
    if re.fullmatch(r"-?\d+\.\d+", val):
        return float(val)
    return val


def _mini_parse(text):
    cfg = {}
    section = None
    for raw in text.splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            continue
        indent = len(line) - len(line.lstrip())
        key, _, val = stripped.partition(":")
        key = key.strip().strip("\"'")
        val = val.strip()
        if indent == 0:
            if val == "":
                section = key
                cfg.setdefault(section, {})
            else:
                cfg[key] = _convert(val)
                section = None
        elif indent >= 2 and section:
            cfg[section][key] = _convert(val)
    return cfg


def _load_file(path):
    if not path.exists():
        return None
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    if yaml:
        try:
            data = yaml.safe_load(text)
            return data if isinstance(data, dict) else None
        except Exception:
            pass
    return _mini_parse(text)


def load(path=None):
    cfg = copy.deepcopy(DEFAULTS)
    bundled = Path(__file__).resolve().parent.parent / "config.yml"
    data = _load_file(bundled)
    if data:
        cfg = _merge(cfg, data)
    path = path or USER_CONFIG
    if isinstance(path, str):
        path = Path(path)
    data = _load_file(path)
    if data:
        cfg = _merge(cfg, data)
    return cfg


def get(cfg, key, default=None):
    val = cfg
    for part in str(key).split("."):
        if not isinstance(val, dict) or part not in val:
            return default
        val = val[part]
    return val


def resolve_dir(cfg, key="download_dir", default=None):
    raw = get(cfg, key) or default or "~/Downloads"
    return os.path.expanduser(str(raw))


def dump_flat(cfg, prefix=""):
    lines = []
    for key, val in cfg.items():
        if isinstance(val, dict):
            lines.extend(dump_flat(val, prefix + key + "."))
        elif isinstance(val, list):
            lines.append(f"{prefix}{key}={json.dumps(val)}")
        elif isinstance(val, bool):
            lines.append(f"{prefix}{key}={'true' if val else 'false'}")
        elif val is None:
            lines.append(f"{prefix}{key}=null")
        else:
            lines.append(f"{prefix}{key}={val}")
    return lines
