#!/usr/bin/env bash
# ─── local-commit installer ───────────────────────────────────────────────
# Usage (curl pipe):
#   curl -fsSL https://git.io/local-commit | bash
#
# Or download & run:
#   curl -fsSLo install.sh https://git.io/local-commit
#   chmod +x install.sh && ./install.sh
#
# Detects your environment and picks the best install method:
#   1. pip install  (if Python 3.9+ available)
#   2. Docker pull  (if Docker available)
#   3. Download pre-built binary (if on GitHub releases page)
# ────────────────────────────────────────────────────────────────────────────

set -euo pipefail

REPO="your-org/local-commit"
VERSION="0.1.0"
BOLD='\033[1m'
GREEN='\033[92m'
CYAN='\033[96m'
YELLOW='\033[93m'
RED='\033[91m'
RESET='\033[0m'

info()  { echo -e "  ${CYAN}i${RESET}  $1"; }
ok()    { echo -e "  ${GREEN}+${RESET}  $1"; }
warn()  { echo -e "  ${YELLOW}!${RESET}  $1"; }
err()   { echo -e "  ${RED}x${RESET}  $1"; }

# ── Preflight checks ─────────────────────────────────────────────────────

has_cmd() { command -v "$1" &>/dev/null; }

PYTHON=""
for candidate in python3 python; do
    if has_cmd "$candidate"; then
        VER=$("$candidate" --version 2>&1 | grep -oP '\d+\.\d+')
        MAJOR="${VER%.*}"
        MINOR="${VER#*.}"
        if [[ "$MAJOR" -ge 3 && "$MINOR" -ge 9 ]] 2>/dev/null; then
            PYTHON="$candidate"
            break
        fi
    fi
done

echo ""
echo "  ${BOLD}local-commit installer${RESET}"
echo ""

# ── Method 1: pip install ───────────────────────────────────────────────

if [[ -n "$PYTHON" ]]; then
    info "Detected Python: $($PYTHON --version)"

    # Check pip
    PIP="${PYTHON} -m pip"
    $PIP --version &>/dev/null || {
        warn "pip not available — trying alternative methods"
        goto_docker
    }

    info "Installing local-commit via pip…"
    $PIP install --quiet "$REPO" 2>/dev/null \
        || $PIP install --quiet "local-commit==$VERSION" 2>/dev/null \
        || {
            # Not on PyPI yet — install from source
            warn "Package not found on PyPI — installing from source"
            TMPDIR=$(mktemp -d)
            cd "$TMPDIR"
            curl -fsSL "https://github.com/$REPO/archive/refs/tags/v$VERSION.tar.gz" \
                | tar xz --strip=1
            $PIP install -e ".[dev]"
            cd - >/dev/null
            rm -rf "$TMPDIR"
        }

    ok "local-commit installed!"
    echo ""
    echo "  Next steps:"
    echo "    local-commit --setup     # download model (one-time)"
    echo "    cd my-project && local-commit"
    echo ""
    exit 0
fi

# ── Method 2: Docker ────────────────────────────────────────────────────

if has_cmd docker; then
    info "Docker detected — pulling image…"
    docker pull "ghcr.io/$REPO:latest" 2>/dev/null \
        || docker build -t local-commit "https://github.com/$REPO.git"

    ok "Docker image ready!"
    echo ""
    echo "  Next steps:"
    echo '    alias lc="docker run --rm -v local-commit-model:/root/.local-commit'
    echo '      -v \"\$(pwd):/repo\" -w /repo local-commit"'
    echo "    lc --setup"
    echo "    lc"
    echo ""
    exit 0
fi

# ── Method 3: Pre-built binary ──────────────────────────────────────────

UNAME_S=$(uname -s 2>/dev/null || echo Linux)
UNAME_M=$(uname -m 2>/dev/null || echo x86_64)

case "$UNAME_S" in
    Linux)  OS="linux" ;;
    Darwin) OS="macos" ;;
    *)      OS="linux" ;;
esac

case "$UNAME_M" in
    x86_64|amd64) ARCH="x86_64" ;;
    aarch64|arm64) ARCH="aarch64" ;;
    *)            ARCH="x86_64" ;;
esac

BINARY="local-commit_${OS}_${ARCH}"
URL="https://github.com/$REPO/releases/download/v$VERSION/$BINARY"

info "Downloading pre-built binary: $BINARY"
if has_cmd curl; then
    curl -fsSLo /usr/local/bin/local-commit "$URL"
elif has_cmd wget; then
    wget -qO /usr/local/bin/local-commit "$URL"
else
    err "Need curl or wget — install one of them and retry."
    exit 1
fi

chmod +x /usr/local/bin/local-commit
ok "Installed to /usr/local/bin/local-commit"
echo ""
echo "  Next:"
echo "    local-commit --setup     # download model"
echo "    local-commit"
echo ""
