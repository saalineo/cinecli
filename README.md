# cinecli

<p align="center">
  <img src="assets/logo-image.png" alt="cinecli logo" width="300">
</p>

Search, stream, and download movies and web series from your terminal — no account, no API keys, no tracking.

```bash
./cinecli "inception"
./cinecli --series "breaking bad"
./cinecli --download -q 1080p "interstellar"
```

## Setup

Run the setup script to install everything:

```bash
./build.sh
```

`build.sh` auto-detects your OS (Ubuntu/Debian, Fedora, Arch, macOS, Alpine) and installs all system and Python dependencies (`python3`, `curl`, `fzf`, `mpv`, `libtorrent`, `beautifulsoup4`, `cloudscraper`, `feedparser`, `rich`, `pyyaml`).

### Manual install

```bash
# Ubuntu/Debian
sudo apt install -y python3 python3-pip curl fzf mpv python3-libtorrent
pip3 install --user beautifulsoup4 cloudscraper feedparser rich pyyaml

# macOS
brew install python@3 curl fzf mpv
pip3 install --user beautifulsoup4 cloudscraper feedparser rich pyyaml libtorrent
```

## Usage

```
./cinecli [options] <movie or tv name>

options:
  -s, --series        search TV series
  -l, --lang <lang>   filter by language (english hindi tamil telugu ...)
  -q, --quality <q>   quality preference (4k 1080p 720p 480p)
  -d, --download      download instead of stream
  -o, --outdir <dir>  output directory (default: ~/Downloads)
  -n, --max <n>       max results per search (default: 50)
  -c, --check         run VPN / DNS-leak checks before searching
  -h, --help          show help
```

### Examples

```bash
./cinecli "inception"
./cinecli --lang hindi "3 idiots"
./cinecli --series "breaking bad"
./cinecli -s --lang korean "squid game"
./cinecli --download -q 1080p --outdir ~/Movies "interstellar"
```

First run will search, then `fzf` lets you pick a title and a quality. It streams (or downloads) automatically.

## Configuration

Settings load from `config.yml` (bundled) with optional override at `~/.config/cinecli/config.yml`.

```yaml
default_quality: 1080p
default_language: english
download_dir: ~/Downloads
max_results: 50
timeout: 30
vpn_required: false
dns_check: false
use_doh: true
player: mpv
```

### Safety

`./cinecli -c <query>` runs VPN and DNS-leak checks before searching. Set `vpn_required: true` in config to block searches when no VPN is detected.

### Sources

cinecli searches TPB, YTS, EZTV, 1337x, Solid, Galaxy, Zooqle, NYAA, Lime, RARBG, and DHT nodes. Enable/disable any in `config.yml` under `sources`.
