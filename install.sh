#!/usr/bin/env sh
# Sirius & the Castle installer for macOS (zsh/bash), Linux, and Windows Git Bash (Windows Terminal).
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
APP_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/castle"
VENV_DIR="$APP_HOME/venv"
BIN_DIR="$HOME/.local/bin"
PATH_LINE='export PATH="$HOME/.local/bin:$PATH"'

find_python() {
    for candidate in python3 python; do
        if command -v "$candidate" >/dev/null 2>&1; then
            if "$candidate" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' >/dev/null 2>&1; then
                printf '%s' "$candidate"
                return 0
            fi
        fi
    done
    return 1
}

if ! PYTHON="$(find_python)"; then
    echo "Error: Python 3.10+ is required (and on Windows, ensure Python is installed rather than the Store stub)." >&2
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
    if [ -f "$HOME/.bashrc" ] || [ -n "${MSYSTEM:-}" ]; then
        add_path_to_file "$HOME/.bashrc"
    fi
    if [ -f "$HOME/.bash_profile" ] || [ -n "${MSYSTEM:-}" ]; then
        add_path_to_file "$HOME/.bash_profile"
    fi
    if [ -f "$HOME/.profile" ]; then
        add_path_to_file "$HOME/.profile"
    fi
}

is_windows_shell=0
case "$(uname -s 2>/dev/null || echo "")" in
    MINGW*|MSYS*|CYGWIN*) is_windows_shell=1 ;;
esac
if [ -n "${MSYSTEM:-}" ]; then
    is_windows_shell=1
fi

if [ "$is_windows_shell" -eq 0 ] && command -v pipx >/dev/null 2>&1; then
    echo "Installing Sirius & the Castle with pipx..."
    pipx install --force "$SCRIPT_DIR"
    pipx ensurepath >/dev/null 2>&1 || true
    ensure_shell_path
else
    echo "Installing Sirius & the Castle into isolated venv ($VENV_DIR)..."
    mkdir -p "$APP_HOME" "$BIN_DIR"
    "$PYTHON" -m venv "$VENV_DIR"

    if [ -x "$VENV_DIR/Scripts/python.exe" ]; then
        "$VENV_DIR/Scripts/python.exe" -m pip install --upgrade pip >/dev/null 2>&1 || true
        "$VENV_DIR/Scripts/python.exe" -m pip install --force-reinstall "$SCRIPT_DIR"
        for cmd in sirius castle; do
            cat > "$BIN_DIR/$cmd" <<EOF
#!/usr/bin/env sh
exec "$VENV_DIR/Scripts/$cmd.exe" "\$@"
EOF
            chmod +x "$BIN_DIR/$cmd"
        done
    else
        "$VENV_DIR/bin/pip" install --upgrade pip >/dev/null 2>&1 || true
        "$VENV_DIR/bin/pip" install --force-reinstall "$SCRIPT_DIR"
        ln -sf "$VENV_DIR/bin/sirius" "$BIN_DIR/sirius"
        ln -sf "$VENV_DIR/bin/castle" "$BIN_DIR/castle"
    fi
    ensure_shell_path
fi

echo ""
echo "✦ Sirius & the Castle installed!"
if [ "$is_windows_shell" -eq 1 ]; then
    echo "Run 'source ~/.bashrc' (or open a new Windows Terminal Git Bash tab), then run: sirius"
else
    echo "Run 'source ~/.zshrc' (or open a new terminal tab), then run: sirius"
fi
