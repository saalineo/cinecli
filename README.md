# cinecli

Search, stream, and download movies from the terminal.

```
./cinecli <search>
```

Three prompts: pick a movie → pick quality → pick action (stream/download).

## Quick start

```bash
git clone <repo-url> && cd cinecli
./cinecli inception
```

First run auto-installs dependencies. After that, just run:

```bash
./cinecli "the matrix"
./cinecli "interstellar 2014"
./cinecli "parasite"
```

## How it works

Two files in the same directory:

| File | Role |
|------|------|
| **`cinecli`** | Bash script — detects your OS, installs deps, runs the search, shows `fzf` menus, builds magnet links, and streams via `webtorrent` |
| **`torrentsearch.py`** | Python script — searches YTS mirrors, falls back to TPB API, prints results as TSV |

The flow:

```
you type: ./cinecli inception
  → cinecli calls torrentsearch.py "inception"
  → torrentsearch.py scrapes YTS → TPB API fallback → prints TSV
  → cinecli shows results in fzf: pick movie → pick quality → pick action
  → cinecli builds magnet link, launches webtorrent → streams to mpv
```

## Platforms

| OS | Package manager | Works? |
|----|---------------|--------|
| Linux (Debian/Ubuntu) | `apt` | ✓ |
| Linux (Arch) | `pacman` | ✓ |
| Linux (Fedora) | `dnf` | ✓ |
| Linux (openSUSE) | `zypper` | ✓ |
| macOS | Homebrew | ✓ |
| Windows | Git Bash / MSYS2 | ✓ |

## Dependencies auto-installed

- `curl`, `fzf`, `mpv`, `python3`
- Node.js + `webtorrent-cli` (or `peerflix` as fallback)

No config files, no API keys, no tracking.
