import os
import re
import sys
import threading
import time

from stream.torrent_client import TorrentClient, save_path_for
from utils.misc import human_size, magnet_for

VIDEO_RE = re.compile(r"\.(mp4|mkv|webm|avi|mov|m4v)$", re.I)

try:
    from rich.progress import BarColumn, DownloadColumn, Progress, TextColumn, TimeRemainingColumn, TransferSpeedColumn

    HAS_RICH = True
except Exception:
    HAS_RICH = False


def _pick(files):
    vids = [(i, n, s) for i, (n, s) in enumerate(files) if VIDEO_RE.search(n) and "sample" not in n.lower()]
    if not vids:
        vids = [(i, n, s) for i, (n, s) in enumerate(files)]
    if not vids:
        return None
    vids.sort(key=lambda v: v[2], reverse=True)
    return vids[0]


def download(magnet, outdir=None, title="", trackers=None, timeout=60, all_files=False, proxy=None):
    tc = TorrentClient(trackers=trackers, timeout=timeout, proxy=proxy)
    save_path = save_path_for(outdir)
    sys.stderr.write("  connecting to swarm...\n")
    tc.add_magnet(magnet, save_path)
    if not tc.wait_metadata(timeout=timeout):
        sys.stderr.write("\r  failed to fetch metadata; torrent may be dead (0 seeders)\n")
        return 1

    files = tc.files()
    if all_files:
        target = (None, "all files", sum(s for _, s in files) if isinstance(files[0], tuple) else 0)
        picked = target
    else:
        picked = _pick(files)
        if not picked:
            sys.stderr.write("\r  no video file found in torrent\n")
            return 1
        tc.file_idx = picked[0]
        tc.file_path = os.path.join(save_path, picked[1])
        tc.set_priorities({picked[0]: 7})

    sys.stderr.write(f"  downloading: {picked[1]} ({human_size(picked[2])}) -> {save_path}\n")

    try:
        if HAS_RICH:
            return _progress_rich(tc, save_path, picked)
        return _progress_plain(tc, save_path, picked)
    finally:
        tc.stop()
    return 0


def _progress_plain(tc, save_path, picked):
    while True:
        st = tc.status()
        if not st:
            break
        if st["progress"] >= 1.0:
            sys.stderr.write("\r  download complete                                    \n")
            break
        pct = st["progress"] * 100
        speed = st["speed"] / 1e6
        eta = st["eta"]
        sys.stderr.write(
            f"\r  {pct:5.1f}%  down {speed:5.2f} MB/s  peers {st['peers']:3d}  eta {eta:4d}s  "
        )
        sys.stderr.flush()
        time.sleep(1)
    path = os.path.join(save_path, picked[1])
    sys.stderr.write(f"\r  saved: {path}\n")
    return 0


def _progress_rich(tc, save_path, picked):
    total = tc.handle.status().total_wanted or picked[2]
    progress = Progress(
        TextColumn("[bold cyan]cinecli[/]", justify="right"),
        BarColumn(bar_width=40),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        DownloadColumn(),
        TransferSpeedColumn(),
        TimeRemainingColumn(),
    )
    with progress:
        task = progress.add_task("downloading", total=total)
        while True:
            st = tc.status()
            if not st:
                break
            progress.update(task, completed=st["progress"] * total)
            if st["progress"] >= 1.0:
                break
            time.sleep(0.5)
    path = os.path.join(save_path, picked[1])
    sys.stderr.write(f"  saved: {path}\n")
    return 0
