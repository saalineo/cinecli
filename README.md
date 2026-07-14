# cinecli

Search, stream, and download movies from the terminal. Scrapes YTS for magnet links and plays them via `webtorrent` + `mpv` with zero configuration.

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

1. **Pick a movie** — results from YTS shown as `Title   Year`
2. **Pick quality** — 720p, 1080p, 2160p depending on availability
3. **Pick action** — stream (instant playback) or download to `~/Downloads/`

Press `Esc` at any prompt to cancel.

### Examples

```bash
./cinecli "Interstellar"
./cinecli "the dark knight 2008"
./cinecli "parasite"
```

## How it works

```
search query  →  yts.mx/browse-movies  →  fzf selects movie
                movie page             →  fzf selects quality/magnet
                magnet                 →  webtorrent --mpv --sequential
```

The `--sequential` flag forces piece-by-piece downloading so `mpv` starts playing within seconds rather than waiting for the full file.

## No tracking

The script is entirely stateless — no logs, no cookies, no API keys. The only network requests are to YTS and the BitTorrent swarm.
