#!/usr/bin/env python3
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.config import load as load_config, dump_flat, get as cfg_get, resolve_dir
from utils.misc import magnet_for, sanitize_field

LANGUAGES = "english hindi tamil telugu malayalam kannada bengali spanish french german japanese korean chinese russian arabic portuguese italian turkish polish dutch"


def cmd_search(args):
    from search.searcher import search

    cfg = load_config()
    results, status, fallback = search(
        args.query,
        mode=args.mode,
        lang=args.lang,
        quality=args.quality,
        max_results=args.max_results,
        cfg=cfg,
    )
    for name, count in status.items():
        sys.stderr.write(f"  {name}: {count} results\n")
    if fallback:
        sys.stderr.write(f"  no language-specific results for '{args.lang}'; showing all matches\n")
    if not results:
        sys.stderr.write("  no results found.\n")
        return 1
    for r in results:
        fields = [
            r.get("source", ""),
            sanitize_field(r.get("title", "")),
            r.get("year", 0),
            r.get("quality", "unknown"),
            r.get("size", "?"),
            r.get("info_hash", ""),
            r.get("seeders", 0),
            sanitize_field(r.get("extra_info", "")),
            r.get("score", 0),
        ]
        print("|".join(str(f) for f in fields))
    return 0


def cmd_config(args):
    cfg = load_config()
    if args.key:
        val = cfg
        for part in args.key.split("."):
            if isinstance(val, dict) and part in val:
                val = val[part]
            else:
                val = None
                break
        print(json.dumps(val) if isinstance(val, (dict, list)) else val if val is not None else "null")
        return 0
    for line in dump_flat(cfg):
        print(line)
    return 0


def cmd_safety(args):
    from utils.safety import check_vpn, dns_leak_check

    vpn, vdetail = check_vpn()
    leak, ldetail = dns_leak_check()
    print(json.dumps({"vpn": vpn, "vpn_detail": vdetail, "dns_leak": leak, "dns_detail": ldetail}))
    return 0


def _build_magnet(args, cfg):
    if args.magnet:
        return args.magnet
    if not args.hash or not re.fullmatch(r"[0-9a-fA-F]{40}", args.hash):
        raise SystemExit(f"  invalid info-hash: {args.hash!r} (expected 40 hex chars)")
    return magnet_for(args.hash, args.title or "", cfg.get("trackers"))


def cmd_stream(args):
    from stream.streamer import stream

    cfg = load_config()
    magnet = _build_magnet(args, cfg)
    player = args.player or cfg_get(cfg, "player", "mpv")
    player_args = cfg_get(cfg, "mpv_args", [])
    proxy = cfg_get(cfg, "proxy")
    return stream(
        magnet,
        title=args.title or "",
        outdir=args.outdir,
        player=player,
        player_args=player_args,
        trackers=cfg.get("trackers"),
        timeout=cfg_get(cfg, "timeout", 30),
        proxy=proxy,
    )


def cmd_download(args):
    from stream.downloader import download

    cfg = load_config()
    magnet = _build_magnet(args, cfg)
    proxy = cfg_get(cfg, "proxy")
    return download(
        magnet,
        outdir=args.outdir or resolve_dir(cfg),
        title=args.title or "",
        trackers=cfg.get("trackers"),
        timeout=cfg_get(cfg, "timeout", 30),
        all_files=args.all_files,
        proxy=proxy,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(prog="cinecli.py", description="cinecli backend")
    sub = parser.add_subparsers(dest="command", required=True)

    p_search = sub.add_parser("search", help="search torrents (pipe-separated output)")
    p_search.add_argument("--mode", choices=["movie", "tv"], default="movie")
    p_search.add_argument("-l", "--lang", default=None)
    p_search.add_argument("-q", "--quality", default=None)
    p_search.add_argument("--max-results", type=int, default=None)
    p_search.add_argument("query")

    p_config = sub.add_parser("config", help="show resolved config")
    p_config.add_argument("key", nargs="?", default=None)

    p_safety = sub.add_parser("safety", help="VPN / DNS-leak checks (json)")

    p_stream = sub.add_parser("stream", help="stream a torrent via mpv/vlc")
    p_stream.add_argument("--magnet", default=None)
    p_stream.add_argument("--hash", default=None)
    p_stream.add_argument("--title", default=None)
    p_stream.add_argument("--outdir", default=None)
    p_stream.add_argument("--player", default=None)

    p_down = sub.add_parser("download", help="download a torrent")
    p_down.add_argument("--magnet", default=None)
    p_down.add_argument("--hash", default=None)
    p_down.add_argument("--title", default=None)
    p_down.add_argument("--outdir", default=None)
    p_down.add_argument("--all-files", action="store_true", help="download every file in the torrent")

    args = parser.parse_args(argv)
    if args.command == "search":
        if args.lang:
            from search.language_detector import canonical_lang

            args.lang = canonical_lang(args.lang)
            if args.lang not in LANGUAGES.split():
                sys.stderr.write(f"  unknown language '{args.lang}'; known: {LANGUAGES}\n")
                return 2
        return cmd_search(args)
    if args.command == "config":
        return cmd_config(args)
    if args.command == "safety":
        return cmd_safety(args)
    if args.command == "stream":
        return cmd_stream(args)
    if args.command == "download":
        return cmd_download(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
