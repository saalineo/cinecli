# cinecli

<p align="center">
  <img src="logos/cinecli.svg" alt="cinecli logo" width="300">
</p>

Search, stream, and download torrent releases from your terminal. No account is
required, but this is not anonymous: index sites, trackers, DHT nodes, peers,
subtitle services, and optional tracker sync can receive network metadata.

```bash
./cinecli "inception"
./cinecli --series "breaking bad"
./cinecli --download -q 1080p "interstellar"
./cinecli --doctor
```

## Setup

Run the setup script to install everything:

```bash
./build.sh
```

`build.sh` auto-detects Ubuntu/Debian, Fedora, Arch, macOS, or Alpine and
installs the system/Python dependencies. It exits with an error if `libtorrent`
is still unavailable, rather than reporting a misleading successful setup.

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

During an interactive search, cinecli opens a live discovery view showing the
query, elapsed time, each source's current state, and the number of results
returned. It automatically falls back to plain diagnostic lines when output is
redirected, so scripting remains reliable.

For normal use, these are the only commands needed:

```bash
./cinecli "movie name"          # guided search and stream
./cinecli -s "series name"      # guided TV search and stream
./cinecli -d "movie name"       # guided download
./cinecli --doctor               # diagnose dependencies/configuration
```

Streaming uses a disposable cache at `~/.cache/cinecli/streams`; normal streamed
files are removed once the player exits. `--outdir` applies to downloads.

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

For proxy use, configure each transport explicitly. Search/index traffic supports
an HTTP proxy; BitTorrent peer traffic requires SOCKS5. A single generic `proxy`
setting is retained only for backward compatibility and is rejected if it cannot
be used safely.

```yaml
http_proxy: http://127.0.0.1:8080
torrent_proxy: socks5://127.0.0.1:1080
```

### Safety

`./cinecli -c <query>` checks for a VPN-like network interface before searching.
It cannot prove that torrent traffic is routed through that interface. DNS leaks
cannot be truthfully verified by a local public-IP comparison, so the tool reports
them as unverified rather than claiming safety. Set `vpn_required: true` to block
searches when no VPN-like interface is detected.

### Sources

cinecli currently has providers for TPB, YTS, EZTV, 1337x, Solid, TorrentGalaxy,
NYAA, LimeTorrents, and BTdig/DHT indexing. Enable/disable any in `config.yml`
under `sources`.
