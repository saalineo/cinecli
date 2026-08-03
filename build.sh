#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# build.sh — one-shot setup for cinecli
# Detects the OS and installs all system + Python dependencies.
# =============================================================================

if command -v apt-get &>/dev/null; then
    OS="debian"
elif command -v dnf &>/dev/null; then
    OS="fedora"
elif command -v pacman &>/dev/null; then
    OS="arch"
elif command -v brew &>/dev/null; then
    OS="macos"
elif command -v apk &>/dev/null; then
    OS="alpine"
else
    echo "unsupported distro (no apt-get/dnf/pacman/brew/apk found)" >&2
    exit 1
fi

echo "detected OS: $OS"

# ---- system packages --------------------------------------------------------
case "$OS" in
    debian)
        echo "installing system packages via apt..."
        sudo apt-get update -qq
        sudo apt-get install -y -qq python3 python3-pip curl fzf mpv
        sudo apt-get install -y -qq python3-libtorrent 2>/dev/null || true
        ;;
    fedora)
        echo "installing system packages via dnf..."
        sudo dnf install -y -q python3 python3-pip curl fzf mpv
        sudo dnf install -y -q python3-libtorrent 2>/dev/null || true
        ;;
    arch)
        echo "installing system packages via pacman..."
        sudo pacman -Sy --noconfirm --quiet python python-pip curl fzf mpv
        sudo pacman -S --noconfirm --quiet python-libtorrent 2>/dev/null || true
        ;;
    macos)
        echo "installing system packages via brew..."
        brew install python@3 curl fzf mpv
        ;;
    alpine)
        echo "installing system packages via apk..."
        apk add --no-cache python3 py3-pip curl fzf mpv
        ;;
esac

# ---- python packages --------------------------------------------------------
echo "installing python packages..."
if [[ "$OS" == "debian" ]] && python3 -c "import libtorrent" 2>/dev/null; then
    echo "libtorrent already available system-wide"
else
    pip3 install --user --break-system-packages libtorrent 2>/dev/null \
        || pip3 install --user libtorrent 2>/dev/null \
        || pip3 install libtorrent 2>/dev/null \
        || echo "WARNING: failed to install libtorrent (streaming/downloading will not work)"
fi

pip3 install --user --break-system-packages beautifulsoup4 cloudscraper feedparser rich pyyaml 2>/dev/null \
    || pip3 install --user beautifulsoup4 cloudscraper feedparser rich pyyaml 2>/dev/null

echo ""
echo "build complete!"
echo ""
echo "  ./cinecli \"inception\"        # search & stream"
echo "  ./cinecli --series \"dark\"    # search TV series"
echo "  ./cinecli -d -q 1080p \"dune\" # download"
