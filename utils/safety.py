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
        return True, "VPN-like interface detected: " + ", ".join(ifaces)
    return False, "no VPN-like network interface detected"


def dns_leak_check():
    """Report an honest limitation instead of a false DNS-leak verdict.

    Comparing a web server's observed public IP after two DNS resolution methods
    cannot establish whether DNS requests leaked. A real test needs a controlled
    authoritative DNS endpoint and must not be represented as a local check.
    """
    return None, {
        "status": "not_verified",
        "detail": "DNS leak verification is unavailable locally; use your VPN provider or a controlled DNS-leak test.",
    }
