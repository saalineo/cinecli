import concurrent.futures
import gzip
import http.client
import json
import random
import socket
import ssl
import time
import urllib.parse
from urllib.parse import urljoin

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.0.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

DOH_SERVERS = [
    ("1.1.1.1", "https://cloudflare-dns.com/dns-query"),
    ("8.8.8.8", "https://dns.google/resolve"),
]

REDIRECT_CODES = (301, 302, 303, 307, 308)


class _PreConnected(http.client.HTTPConnection):
    def __init__(self, sock, timeout):
        super().__init__("sni.invalid", timeout=timeout)
        self._pre = sock

    def connect(self):
        self.sock = self._pre


def _is_ip(host):
    try:
        socket.inet_pton(socket.AF_INET, host)
        return True
    except Exception:
        return False


def _single_ip(host):
    try:
        infos = socket.getaddrinfo(host, None, socket.AF_INET, socket.SOCK_STREAM)
        if infos:
            return infos[0][4][0]
    except Exception:
        pass
    return host


def _tls_connect(ip, port, host, timeout, ctx):
    target = ip if _is_ip(ip) else _single_ip(ip)
    raw = socket.create_connection((target, port), timeout=timeout)
    return ctx.wrap_socket(raw, server_hostname=host)


class RateLimiter:
    def __init__(self, rate, per):
        self.rate = rate
        self.per = per
        self.tokens = {}
        self.last = {}

    def acquire(self, key):
        now = time.monotonic()
        tokens = self.tokens.get(key, self.rate)
        last = self.last.get(key, now)
        tokens = min(self.rate, tokens + (now - last) * self.rate / self.per)
        if tokens >= 1:
            self.tokens[key] = tokens - 1
            self.last[key] = now
            return
        wait = (1 - tokens) * self.per / self.rate
        if wait > 0:
            time.sleep(wait)
        self.tokens[key] = 0
        self.last[key] = now + wait


class DohResolver:
    def __init__(self):
        self._cache = {}
        self._disabled = False

    def query(self, host):
        if self._disabled:
            return None
        hit = self._cache.get(host)
        if hit and time.time() - hit[1] < 300:
            return hit[0]
        for ip, base in DOH_SERVERS:
            try:
                p = urllib.parse.urlsplit(base)
                path = p.path or "/"
                sep = "&" if p.query else "?"
                url_path = f"{path}{sep}name={host}&type=A"
                ctx = ssl.create_default_context()
                sock = socket.create_connection((ip, 443), timeout=3)
                tls = ctx.wrap_socket(sock, server_hostname=p.hostname)
                conn = _PreConnected(tls, 3)
                conn.request("GET", url_path, headers={
                    "Accept": "application/dns-json",
                    "User-Agent": random.choice(USER_AGENTS),
                })
                resp = conn.getresponse()
                body = resp.read()
                conn.close()
                data = json.loads(body.decode("utf-8", "replace"))
                answers = [a["data"] for a in data.get("Answer", []) if a.get("type") == 1]
                if answers:
                    self._cache[host] = (answers, time.time())
                    return answers
            except Exception:
                continue
        self._cache[host] = (None, time.time())
        self._disabled = True
        return None


class Net:
    def __init__(self, timeout=30, proxy=None, use_doh=True, rate_per_minute=30):
        self.timeout = timeout
        self.proxy = proxy
        self.use_doh = use_doh
        self.doh = DohResolver()
        self._cookies = {}
        self.limiter = RateLimiter(rate_per_minute, 60)

    def get(self, url, source=None, headers=None, retries=1, binary=False):
        if source:
            self.limiter.acquire(source)
        for attempt in range(max(1, retries)):
            try:
                status, data = self._request(url, headers or {}, binary=binary, redirects=0)
                if status and 200 <= status < 400:
                    return data
                if status == 429:
                    time.sleep(2 + attempt)
                elif status and 400 <= status < 500:
                    return None
            except Exception:
                time.sleep(0.5 * (attempt + 1))
        return None

    def parallel_get(self, urls, sources=None, headers=None, retries=1, binary=False):
        if not urls:
            return {}
        sources = sources or [None] * len(urls)

        def work(url, src):
            return url, self.get(url, source=src, headers=headers, retries=retries, binary=binary)

        results = {}
        workers = min(8, len(urls))
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(work, url, src) for url, src in zip(urls, sources)]
            for future in concurrent.futures.as_completed(futures):
                url, data = future.result()
                results[url] = data
        return results

    def _store_cookies(self, resp):
        for key, value in resp.getheaders():
            if key.lower() != "set-cookie":
                continue
            pair = value.partition(";")[0].partition("=")
            if pair[1] and pair[0]:
                self._cookies[pair[0].strip()] = pair[2].strip()

    def _cookie_header(self):
        return "; ".join(f"{k}={v}" for k, v in self._cookies.items())

    def _request(self, url, headers, binary, redirects):
        if redirects > 5:
            return None, None
        p = urllib.parse.urlsplit(url)
        if p.scheme not in ("http", "https") or not p.hostname:
            return None, None
        host = p.hostname
        ip = host
        if self.use_doh and p.scheme == "https":
            ips = self.doh.query(host)
            if ips:
                ip = random.choice(ips)

        path = p.path or "/"
        if p.query:
            path += "?" + p.query

        hdrs = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "*/*",
            "Accept-Encoding": "identity",
        }
        hdrs.update(headers)
        hdrs.setdefault("Host", host)
        if self._cookies:
            hdrs.setdefault("Cookie", self._cookie_header())

        ctx = ssl.create_default_context()
        proxy_p = urllib.parse.urlsplit(self.proxy) if self.proxy else None

        if p.scheme == "https":
            if proxy_p and proxy_p.hostname:
                tunnel_headers = {}
                if proxy_p.username:
                    import base64
                    token = base64.b64encode(
                        f"{proxy_p.username}:{proxy_p.password or ''}".encode()
                    ).decode()
                    tunnel_headers["Proxy-Authorization"] = "Basic " + token
                proxy_conn = http.client.HTTPConnection(
                    proxy_p.hostname, proxy_p.port or 443, timeout=self.timeout
                )
                proxy_conn.set_tunnel(host, p.port or 443, headers=tunnel_headers)
                proxy_conn.connect()
                tls = ctx.wrap_socket(proxy_conn.sock, server_hostname=host)
                conn = _PreConnected(tls, self.timeout)
            else:
                tls = _tls_connect(ip, p.port or 443, host, self.timeout, ctx)
                conn = _PreConnected(tls, self.timeout)
            req_url = path
        else:
            if proxy_p and proxy_p.hostname:
                conn = http.client.HTTPConnection(
                    proxy_p.hostname, proxy_p.port or 80, timeout=self.timeout
                )
                req_url = url
            else:
                conn = http.client.HTTPConnection(host, p.port or 80, timeout=self.timeout)
                req_url = path

        try:
            conn.request("GET", req_url, headers=hdrs)
            resp = conn.getresponse()
            status = resp.status
            self._store_cookies(resp)
            location = resp.getheader("Location")
            if status in REDIRECT_CODES and location:
                conn.close()
                return self._request(urljoin(url, location), headers, binary, redirects + 1)
            data = resp.read()
            conn.close()
            encoding = (resp.getheader("Content-Encoding") or "").lower()
            if encoding == "gzip" and data[:2] == b"\x1f\x8b":
                data = gzip.decompress(data)
            return status, (data if binary else data.decode("utf-8", "replace"))
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            raise
