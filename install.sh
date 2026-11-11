#!/usr/bin/env sh
# Sirius & the Castle installer for macOS & Linux terminals (zsh & bash).
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
APP_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/castle"
VENV_DIR="$APP_HOME/venv"
BIN_DIR="$HOME/.local/bin"
PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'

if command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
elif command -v python >/dev/null 2>&1; then
    PYTHON=python
else
    echo "Error: Python 3.10+ is required." >&2
    exit 1
fi

add_path_to_file() {
    rc_file="$1"
    [ -f "$rc_file" ] || touch "$rc_file"
    if ! grep -Fq '.local/bin' "$rc_file" 2>/dev/null; then
        printf '\n# Added by Castle (Sirius)\n%s\n' "$PATH_LINE" >> "$rc_file"
        echo "Updated $rc_file to include ~/.local/bin"
    fi
}

ensure_shell_path() {
    case "${SHELL:-}" in
        */zsh) add_path_to_file "$HOME/.zshrc" ;;
    esac
    if command -v zsh >/dev/null 2>&1 || [ -f "$HOME/.zshrc" ]; then
        add_path_to_file "$HOME/.zshrc"
    fi
    if [ -f "$HOME/.zprofile" ]; then
        add_path_to_file "$HOME/.zprofile"
    fi

    case "${SHELL:-}" in
        */bash) add_path_to_file "$HOME/.bashrc" ;;
    esac
    if [ -f "$HOME/.bashrc" ]; then
        add_path_to_file "$HOME/.bashrc"
    fi
    if [ -f "$HOME/.profile" ]; then
        add_path_to_file "$HOME/.profile"
    fi
}

if command -v pipx >/dev/null 2>&1; then
    echo "Installing Castle (sirius) with pipx..."
    pipx install --force "$SCRIPT_DIR"
    pipx ensurepath >/dev/null 2>&1 || true
    ensure_shell_path
else
    echo "Installing Castle (sirius) into isolated venv ($VENV_DIR)..."
    mkdir -p "$APP_HOME" "$BIN_DIR"
    "$PYTHON" -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --upgrade pip >/dev/null
    "$VENV_DIR/bin/pip" install --force-reinstall "$SCRIPT_DIR"
    ln -sf "$VENV_DIR/bin/sirius" "$BIN_DIR/sirius"
    ln -sf "$VENV_DIR/bin/castle" "$BIN_DIR/castle"
    ensure_shell_path
fi

echo ""
echo "Castle installed! To use 'sirius' in this already-open terminal, run:"
echo "  source ~/.zshrc   # (or open any new terminal window/tab)"
