# cinecli

Search, stream, and download movies from the terminal.

```bash
./cinecli <movie name>
```

Pick a movie, pick a quality, and it downloads (or streams) automatically.

## Usage

```bash
./cinecli inception
./cinecli "the matrix"
./cinecli "interstellar 2014"
./cinecli "parasite"
```

First run installs dependencies automatically. After that, just search.

## What happens

1. You type `./cinecli <movie name>`
2. Pick a movie from the list
3. Pick a quality / release
4. Downloads to `~/Downloads/` (or `$OUTDIR`)

## Platforms

Linux, macOS, Windows (Git Bash / MSYS2).

## Dependencies

Auto-installed on first run: `curl`, `fzf`, `python3`, `node`, `webtorrent-cli`.

No config files, no API keys, no tracking.

By Dev, For Dev, of Dev
