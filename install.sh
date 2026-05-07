#!/usr/bin/env bash
set -euo pipefail

ITERM_ENV_BASE="$HOME/Library/Application Support/iTerm2/iterm2env/versions"

find_python() {
    [[ -d "$ITERM_ENV_BASE" ]] || return 1
    find "$ITERM_ENV_BASE" -name "python3" -path "*/bin/python3" 2>/dev/null | sort -V | tail -1
}

PYTHON=$(find_python || true)

if [[ -z "$PYTHON" ]]; then
    echo "Error: iTerm2 Python API environment not found."
    echo "Enable it in: iTerm2 → Settings → General → Magic → Enable Python API"
    exit 1
fi

echo "Found: $PYTHON"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT="$SCRIPT_DIR/iterm_theme.py"

if [[ ! -f "$SCRIPT" ]]; then
    echo "Error: iterm_theme.py not found in $SCRIPT_DIR"
    exit 1
fi

case "$SHELL" in
    */zsh)  RC="$HOME/.zshrc" ;;
    */bash) RC="$HOME/.bash_profile" ;;
    *)      RC="$HOME/.profile" ;;
esac

ALIAS_LINE="alias theme='\"$PYTHON\" \"$SCRIPT\"'"

if grep -qF "alias theme=" "$RC" 2>/dev/null; then
    echo "Replacing existing 'theme' alias in $RC"
    sed -i '' "/alias theme=/d" "$RC"
fi

echo "$ALIAS_LINE" >> "$RC"

echo "Added to $RC:"
echo "  $ALIAS_LINE"
echo ""
echo "Reload with: source $RC"
echo "Then run:    theme"
