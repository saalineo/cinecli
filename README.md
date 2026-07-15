# cinecli

Search, stream, and download movies from the terminal. Scrapes multiple torrent sites for magnet links and plays them via `webtorrent` + `mpv`.

## Dependencies

- `curl` — HTTP requests
- `fzf` — interactive selection UI
- `webtorrent-cli` — BitTorrent streaming engine
- `mpv` — media player

```bash
# Arch
sudo pacman -S curl fzf mpv && npm install -g webtorrent-cli

# Ubuntu/Debian
sudo apt install curl fzf mpv && npm install -g webtorrent-cli

# macOS
brew install curl fzf mpv && npm install -g webtorrent-cli
```

## Usage

```
./cinecli <search query>
```

Three sequential prompts:

1. **Pick a movie** — results from available sources, shown as `Title   Year`
2. **Pick quality** — resolution options for the selected movie
3. **Pick action** — stream (instant playback) or download to `~/Downloads/`

Press `Esc` at any prompt to cancel.

### Examples

```bash
./cinecli "Interstellar"
./cinecli "the dark knight 2008"
./cinecli "parasite"
```

## Sources

The script tries each source in order until one returns results:

| Source | Code | Status |
|--------|------|--------|
| YTS (yts.lt, yts.rs, yts.do...) | `yts` | domain-rotating, sometimes blocked |
| 1337x | `1337x` | generally reliable |
| TorrentGalaxy | `tgx` | fallback |

## Configuration

Config file at `~/.config/cinecli/config`:

```bash
SOURCES="yts,1337x,tgx"       # priority order
PROXY=""                      # e.g. socks5://127.0.0.1:1080
OUTDIR="$HOME/Downloads"      # download location
```

Every config value can be overridden by a `CINECLI_*` env var:

```bash
CINECLI_SOURCES="1337x,tgx"                    # skip YTS
CINECLI_PROXY="socks5://127.0.0.1:1080"       # route through proxy
CINECLI_BASE_URL="https://yts.lt"              # pin a YTS domain
```

## How it works

```
search  →  try yts → try 1337x → try tgx  →  fzf selects movie
            movie detail page               →  fzf selects quality/magnet
            magnet                           →  webtorrent --mpv --sequential
```

The `--sequential` flag forces piece-by-piece downloading so `mpv` starts playing within seconds.

## No tracking

The script is entirely stateless — no logs, no cookies, no API keys. The only network requests are to the torrent sites and the BitTorrent swarm.
