import http.server
import os
import re
import subprocess
import sys
import threading
import time

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
    index = 0
    path_name = ""

    def _serve(self, head_only=False):
        idx = self.tc.file_idx
        name = self.tc.file_name
        size = self.tc.file_size
        ext = VIDEO_RE.search(name)
        mime = MIME.get(ext.group(1).lower()) if ext else "video/mp4"
        rng = self.headers.get("Range")

        avail = self.tc.downloaded_bytes(idx)
        if avail is None:
            avail = size

        if rng and rng.startswith("bytes="):
            start_s, _, end_s = rng[6:].partition("-")
            start = int(start_s) if start_s else 0
            end = int(end_s) if end_s else size - 1
            end = min(end, size - 1)
            if start > size - 1:
                self.send_response(416)
                self.send_header("Content-Range", f"bytes */{size}")
                self.end_headers()
                return
            length = min(end - start + 1, max(0, avail - start))
            waited = 0
            while length <= 0 and waited < 30:
                time.sleep(0.3)
                waited += 0.3
                avail = self.tc.downloaded_bytes(idx) or avail
                length = min(end - start + 1, max(0, avail - start))
            if length <= 0:
                self.send_response(204)
                self.end_headers()
                return
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{start + length - 1}/{size}")
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
            self._pump(idx, 0, min(size, max(avail, 0)))

    def _pump(self, idx, start, length):
        offset = start
        remaining = length
        while remaining > 0:
            chunk = self.tc.read_chunk(idx, offset, min(256 * 1024, remaining))
            if chunk:
                try:
                    self.wfile.write(chunk)
                except (BrokenPipeError, ConnectionResetError):
                    return
                offset += len(chunk)
                remaining -= len(chunk)
            else:
                time.sleep(0.3)

    def do_GET(self):
        self._serve(head_only=False)

    def do_HEAD(self):
        self._serve(head_only=True)

    def log_message(self, fmt, *args):
        pass


class _Server(threading.Thread):
    def __init__(self, handler, tc):
        super().__init__(daemon=True)
        self.tc = tc
        self.httpd = None
        self.port = None

    def run(self):
        self.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), _RangeHandler)
        _RangeHandler.tc = self.tc
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

    sys.stderr.write(f"  streaming: {name} ({human_size(size)})\n")

    server = _Server(_RangeHandler, tc)
    server.start()
    for _ in range(100):
        if server.port:
            break
        time.sleep(0.05)

    stop = threading.Event()
    progress = threading.Thread(target=_progress_loop, args=(tc, stop), daemon=True)
    progress.start()

    url = f"http://127.0.0.1:{server.port}/"
    args = [player, "--force-window", url]
    if player_args:
        args[1:1] = player_args
    try:
        subprocess.call(args)
    except FileNotFoundError:
        sys.stderr.write(f"\r  player '{player}' not found; install mpv or vlc\n")
        stop.set()
        server.stop()
        tc.stop()
        return 1
    finally:
        stop.set()
        server.stop()
        tc.stop()
    sys.stderr.write("\r  done\n")
    return 0
