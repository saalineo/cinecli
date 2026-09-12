import http.server
import os
import re
import subprocess
import sys
import threading
import time
import urllib.parse

from stream.torrent_client import TorrentClient, save_path_for
from utils.misc import human_size, magnet_for

MIME = {
    "mp4": "video/mp4",
    "mkv": "video/x-matroska",
    "webm": "video/webm",
    "avi": "video/x-msvideo",
    "mov": "video/quicktime",
    "m4v": "video/x-m4v",
}

VIDEO_RE = re.compile(r"\.(mp4|mkv|webm|avi|mov|m4v)$", re.I)


class _RangeHandler(http.server.BaseHTTPRequestHandler):
    tc = None
    stop_event = None

    def _serve(self, head_only=False):
        if not self.tc or getattr(self.tc, "file_idx", None) is None:
            self.send_error(404, "No stream active")
            return

        idx = self.tc.file_idx
        name = self.tc.file_name
        size = self.tc.file_size
        ext = VIDEO_RE.search(name)
        mime = MIME.get(ext.group(1).lower()) if ext else "video/mp4"
        rng = self.headers.get("Range")

        if rng and rng.startswith("bytes="):
            parts = rng[6:].strip().split("-")
            start_s = parts[0]
            end_s = parts[1] if len(parts) > 1 else ""

            if not start_s and end_s:
                try:
                    suffix = int(end_s)
                    start = max(0, size - suffix)
                    end = size - 1
                except ValueError:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.end_headers()
                    return
            else:
                try:
                    start = int(start_s) if start_s else 0
                    end = int(end_s) if end_s else size - 1
                except ValueError:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.end_headers()
                    return

            if start >= size or start < 0 or end < start:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.end_headers()
                return

            end = min(end, size - 1)
            length = end - start + 1

            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.send_header("Content-Length", str(length))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Type", mime)
            self.end_headers()
            if head_only:
                return
            self._pump(idx, start, length)
        else:
            self.send_response(200)
            self.send_header("Content-Length", str(size))
            self.send_header("Accept-Ranges", "bytes")
            self.send_header("Content-Type", mime)
            self.end_headers()
            if head_only:
                return
            self._pump(idx, 0, size)

    def _pump(self, idx, start, length):
        offset = start
        remaining = length
        chunk_size = 256 * 1024
        while remaining > 0:
            if self.stop_event and self.stop_event.is_set():
                break
            to_read = min(chunk_size, remaining)
            chunk = self.tc.read_chunk_blocking(idx, offset, to_read, timeout=40, stop_event=self.stop_event)
            if not chunk:
                break
            try:
                self.wfile.write(chunk)
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                return
            offset += len(chunk)
            remaining -= len(chunk)

    def do_GET(self):
        self._serve(head_only=False)

    def do_HEAD(self):
        self._serve(head_only=True)

    def log_message(self, fmt, *args):
        pass


class _Server(threading.Thread):
    def __init__(self, tc, stop_event):
        super().__init__(daemon=True)
        self.tc = tc
        self.stop_event = stop_event
        self.httpd = None
        self.port = None

    def run(self):
        _RangeHandler.tc = self.tc
        _RangeHandler.stop_event = self.stop_event
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _RangeHandler)
        self.port = self.httpd.server_address[1]
        self.httpd.serve_forever()

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()


def _progress_loop(tc, stop):
    while not stop.is_set():
        st = tc.status()
        if st:
            pct = st["progress"] * 100
            speed = st["speed"] / 1e6
            eta = st["eta"]
            sys.stderr.write(
                f"\r  {pct:5.1f}%  down {speed:5.2f} MB/s  peers {st['peers']:3d}  "
                f"state {st['state']}  eta {eta:4d}s  "
            )
            sys.stderr.flush()
        time.sleep(2)


def pick_video(files):
    vids = [(i, n, s) for i, (n, s) in enumerate(files) if VIDEO_RE.search(n) and "sample" not in n.lower()]
    if not vids:
        vids = [(i, n, s) for i, (n, s) in enumerate(files)]
    if not vids:
        return None
    vids.sort(key=lambda v: v[2], reverse=True)
    return vids[0]


def stream(magnet, title="", outdir=None, player="mpv", player_args=None, trackers=None, timeout=60, proxy=None):
    tc = TorrentClient(trackers=trackers, timeout=timeout, proxy=proxy)
    save_path = save_path_for(outdir or "/tmp")
    sys.stderr.write("  connecting to swarm...\n")
    tc.add_magnet(magnet, save_path)
    if not tc.wait_metadata(timeout=timeout):
        sys.stderr.write("\r  failed to fetch metadata; torrent may be dead (0 seeders)\n")
        return 1

    files = tc.files()
    picked = pick_video(files)
    if not picked:
        sys.stderr.write("\r  no video file found in torrent\n")
        return 1
    idx, name, size = picked
    tc.file_idx = idx
    tc.file_name = name
    tc.file_size = size
    tc.file_path = os.path.join(save_path, name)
    tc.set_priorities({idx: 7})
    tc.set_sequential(True)

    # Prioritize file header (first 4MB) and tail (last 4MB) for MP4/MKV container metadata
    head_pr = tc.piece_range_for(idx, 0, min(size, 4 * 1024 * 1024))
    if head_pr:
        tc.prioritize_range(head_pr[0], head_pr[1], deadline=0)
    if size > 4 * 1024 * 1024:
        tail_pr = tc.piece_range_for(idx, size - 4 * 1024 * 1024, 4 * 1024 * 1024)
        if tail_pr:
            tc.prioritize_range(tail_pr[0], tail_pr[1], deadline=0)

    sys.stderr.write(f"  streaming: {name} ({human_size(size)})\n")

    stop = threading.Event()
    server = _Server(tc, stop)
    server.start()
    for _ in range(100):
        if server.port:
            break
        time.sleep(0.05)

    progress = threading.Thread(target=_progress_loop, args=(tc, stop), daemon=True)
    progress.start()

    sys.stderr.write("  buffering stream...\n")
    tc.wait_for_range(idx, 0, min(size, 512 * 1024), timeout=30, stop_event=stop)

    safe_name = urllib.parse.quote(name)
    url = f"http://127.0.0.1:{server.port}/{safe_name}"
    args = [player]
    if player == "mpv":
        args.extend(["--no-ytdl", "--force-window"])
        if title:
            args.append(f"--force-media-title={title}")
    elif player == "vlc":
        if title:
            args.append(f"--meta-title={title}")
    else:
        args.append("--force-window")

    if player_args:
        args.extend(player_args)
    args.append(url)

    ret = 0
    try:
        ret = subprocess.call(args)
    except FileNotFoundError:
        sys.stderr.write(f"\r  player '{player}' not found; install mpv or vlc\n")
        ret = 1
    finally:
        stop.set()
        server.stop()
        tc.stop()
    if ret == 0:
        sys.stderr.write("\r  done\n")
    return ret
