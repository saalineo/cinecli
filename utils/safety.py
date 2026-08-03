import re
import subprocess


def vpn_interfaces():
    names = []
    try:
        out = subprocess.run(
            ["ip", "-brief", "addr"], capture_output=True, text=True, timeout=5
        ).stdout
        names = re.findall(r"^([\w.:-]+)\s", out, re.M)
    except Exception:
        try:
            with open("/proc/net/dev", encoding="utf-8") as fh:
                names = re.findall(r"^\s*([\w.:-]+):\s*", fh.read(), re.M)
        except Exception:
            pass
    return [n for n in names if re.search(r"(tun|tap|ppp|wg|ipsec|utun|nordlynx|tailscale|zerotier)", n, re.I)]


def check_vpn():
    ifaces = vpn_interfaces()
    if ifaces:
        return True, "vpn interface: " + ", ".join(ifaces)
    return False, "no vpn interface detected"


def _public_ip(doh):
    if doh:
        from utils.network import Net

        net = Net(timeout=12, use_doh=True)
        return net.get("https://api.ipify.org", source="dnscheck")
    import urllib.request

    try:
        return urllib.request.urlopen("https://api.ipify.org", timeout=8).read().decode()
    except Exception:
        return None


def dns_leak_check():
    local = _public_ip(False)
    doh = _public_ip(True)
    if local and doh:
        return local != doh, {"system_dns_ip": local, "doh_ip": doh}
    if local and not doh:
        return None, {"system_dns_ip": local, "doh_ip": None}
    return None, {"system_dns_ip": None, "doh_ip": None}
