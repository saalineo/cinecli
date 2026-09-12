import os
import socket
import time

try:
    import libtorrent as lt

    LIBTORRENT_OK = True
except Exception:
    lt = None
    LIBTORRENT_OK = False

INSTALL_HINT = (
    "python-libtorrent is required for streaming/downloading.\n"
    "  pip install libtorrent\n"
    "  or (Debian/Ubuntu): sudo apt install python3-libtorrent"
)

DHT_NODES = [
    ("router.bittorrent.com", 6881),
    ("dht.transmissionbt.com", 6881),
    ("router.utorrent.com", 6881),
    ("dht.aelitis.com", 6881),
    ("dht.libtorrent.org", 25401),
]

NEW_API = LIBTORRENT_OK and not hasattr(lt, "settings_pack")

_ALERT_NAMES = ["error_notification", "tracker_notification"]


def _apply_proxy(settings, proxy):
    if not proxy:
        return
    pp = proxy.split("://")[-1]
    user = pw = ""
    if "@" in pp:
        creds, pp = pp.rsplit("@", 1)
        user, _, pw = creds.partition(":")
    host, _, port = pp.partition(":")
    settings["proxy_hostname"] = host
    settings["proxy_port"] = int(port or 1080)
    settings["proxy_type"] = (
        int(lt.proxy_type_t.socks5_pw) if user else int(lt.proxy_type_t.socks5)
    )
    settings["proxy_username"] = user
    settings["proxy_password"] = pw
    settings["proxy_torrents"] = True
    settings["proxy_peer_connections"] = True


def _apply_settings(obj, settings):
    for key, value in settings.items():
        try:
            obj[key] = value
        except Exception:
            pass


def _make_session(trackers, proxy, timeout):
    common = {
        "user_agent": "cinecli/2.0",
        "enable_dht": True,
        "enable_lsd": True,
        "enable_upnp": False,
        "enable_natpmp": False,
        "announce_to_all_trackers": True,
        "announce_to_all_tiers": True,
        "active_downloads": 1,
        "active_limit": 1,
    }
    if NEW_API:
        ds = lt.default_settings()
        ds["listen_interfaces"] = "0.0.0.0:6881"
        if "session_timeout" in ds:
            ds["session_timeout"] = timeout
        elif "connection_timeout" in ds:
            ds["connection_timeout"] = timeout
        _apply_settings(ds, common)
        mask = 0
        cat = lt.alert.category_t
        for name in _ALERT_NAMES:
            mask |= int(getattr(cat, name))
        ds["alert_mask"] = mask
        _apply_proxy(ds, proxy)
        return lt.session(lt.session_params(ds))
    sp = lt.settings_pack()
    sp["listen_interfaces"] = "0.0.0.0:6881,[::]:6881"
    sp["connection_timeout"] = timeout
    _apply_settings(sp, common)
    sp["alert_mask"] = (
        lt.alert.category_t.error_notification | lt.alert.category_t.tracker_notification
    )
    _apply_proxy(sp, proxy)
    return lt.session(sp)


class TorrentClient:
    def __init__(self, trackers=None, timeout=30, proxy=None):
        if not LIBTORRENT_OK:
            raise RuntimeError(INSTALL_HINT)
        self.trackers = trackers or []
        self.timeout = timeout
        self.session = _make_session(self.trackers, proxy, timeout)
        for host, port in DHT_NODES:
            try:
                self.session.add_dht_router(host, port)
            except Exception:
                pass
        self.handle = None

    def add_magnet(self, magnet, save_path):
        try:
            at = lt.parse_magnet_uri(magnet)
        except Exception as exc:
            raise RuntimeError(f"invalid magnet: {exc}") from exc
        at.save_path = save_path
        at.user_agent = "cinecli/2.0"
        try:
            self.handle = self.session.add_torrent(at)
        except Exception as exc:
            raise RuntimeError(f"failed to add torrent: {exc}") from exc

    def pop_errors(self):
        errors = []
        try:
            for alert in self.session.pop_alerts():
                if alert.category() & lt.alert.category_t.error_notification:
                    errors.append(str(alert.message()))
        except Exception:
            pass
        return errors

    def wait_metadata(self, timeout=None):
        if not self.handle:
            return False
        deadline = time.time() + (timeout or self.timeout)
        while time.time() < deadline:
            if self.handle.has_metadata():
                return True
            self.pop_errors()
            time.sleep(0.1)
        return self.handle.has_metadata()

    def torrent_info(self):
        return self.handle.torrent_file()

    def files(self):
        fs = self.torrent_info().files()
        return [(fs.file_path(i), fs.file_size(i)) for i in range(fs.num_files())]

    def set_priorities(self, index_map):
        if not self.handle or not self.handle.has_metadata():
            return
        n = self.torrent_info().num_files()
        priorities = [0] * n
        for idx, prio in index_map.items():
            if 0 <= idx < n:
                priorities[idx] = prio
        try:
            self.handle.prioritize_files(priorities)
        except Exception:
            pass

    def set_sequential(self, sequential=True):
        if self.handle and self.handle.has_metadata():
            try:
                self.handle.set_sequential_download(sequential)
            except Exception:
                pass

    def piece_range_for(self, file_idx, offset, length):
        if not self.handle or not self.handle.has_metadata():
            return None
        try:
            ti = self.torrent_info()
            fs = ti.files()
            piece_len = ti.piece_length()
            if piece_len <= 0:
                return None
            base_offset = fs.file_offset(file_idx)
            first_p = (base_offset + offset) // piece_len
            last_p = (base_offset + max(0, offset + length - 1)) // piece_len
            num_pieces = ti.num_pieces()
            first_p = max(0, min(first_p, num_pieces - 1))
            last_p = max(0, min(last_p, num_pieces - 1))
            return (first_p, last_p)
        except Exception:
            return None

    def have_pieces(self, first_piece, last_piece):
        if not self.handle:
            return False
        try:
            return all(self.handle.have_piece(p) for p in range(first_piece, last_piece + 1))
        except Exception:
            return False

    def prioritize_range(self, first_piece, last_piece, deadline=0):
        if not self.handle:
            return
        for p in range(first_piece, last_piece + 1):
            try:
                if not self.handle.have_piece(p):
                    self.handle.set_piece_deadline(p, deadline)
            except Exception:
                pass

    def wait_for_range(self, file_idx, offset, length, timeout=30, stop_event=None):
        pr = self.piece_range_for(file_idx, offset, length)
        if not pr:
            return True
        first_p, last_p = pr
        if self.have_pieces(first_p, last_p):
            return True
        self.prioritize_range(first_p, last_p, deadline=0)
        start_time = time.time()
        while time.time() - start_time < timeout:
            if stop_event and stop_event.is_set():
                return False
            if self.have_pieces(first_p, last_p):
                return True
            time.sleep(0.05)
        return self.have_pieces(first_p, last_p)

    def read_chunk(self, index, offset, length):
        path = getattr(self, "file_path", None)
        if not path:
            return b""
        try:
            with open(path, "rb") as fh:
                fh.seek(offset)
                return fh.read(length)
        except OSError:
            return b""

    def read_chunk_blocking(self, index, offset, length, timeout=30, stop_event=None):
        if not self.wait_for_range(index, offset, length, timeout=timeout, stop_event=stop_event):
            return b""
        return self.read_chunk(index, offset, length)

    def status(self):
        if not self.handle:
            return None
        st = self.handle.status()
        total = st.total_wanted
        done = st.total_wanted_done
        remaining = max(0, total - done)
        speed = st.download_rate
        eta = remaining // speed if speed > 0 else 0
        return {
            "progress": done / total if total else 0,
            "speed": speed,
            "peers": st.num_peers,
            "seeds": st.num_seeds,
            "eta": eta,
            "state": _state_name(st),
        }

    def pause(self):
        if self.handle:
            self.handle.pause()

    def stop(self):
        try:
            self.session.pause()
            self.session = None
        except Exception:
            pass


def _state_name(st):
    state = st.state
    if hasattr(state, "name"):
        return state.name
    names = [
        "queued", "checking", "downloading_metadata", "downloading",
        "finished", "seeding", "allocating", "checking_resume_data",
    ]
    if isinstance(state, int) and 0 <= state < len(names):
        return names[state]
    return str(state)


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def save_path_for(outdir, title=""):
    base = os.path.expanduser(outdir or os.path.join(os.path.expanduser("~"), "Downloads"))
    os.makedirs(base, exist_ok=True)
    return base
