"""Cross-platform keyboard input and line-editing helpers (Windows msvcrt + POSIX termios)."""

from contextlib import contextmanager
from dataclasses import dataclass, field
import os
import sys
import time

if sys.platform == "win32":
    import msvcrt
else:
    import select
    import termios

_WIN_EXTENDED_MAP = {
    b"H": "UP",
    b"P": "DOWN",
    b"K": "LEFT",
    b"M": "RIGHT",
    b"G": "HOME",
    b"O": "END",
    b"S": "DELETE",
}

_ANSI_ARROWS = {
    b"A": "UP",
    b"B": "DOWN",
    b"C": "RIGHT",
    b"D": "LEFT",
    b"H": "HOME",
    b"F": "END",
}

_posix_depth = 0
_posix_saved_termios = None


def _apply_posix_raw(fd: int) -> None:
    mode = termios.tcgetattr(fd)
    mode[3] &= ~(termios.ICANON | termios.ECHO | termios.ISIG)
    mode[6][termios.VMIN] = 1
    mode[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSADRAIN, mode)


@contextmanager
def keyboard_session():
    """Put stdin into non-canonical, no-echo mode on POSIX; no-op on Windows/non-TTY."""
    global _posix_depth, _posix_saved_termios

    if sys.platform == "win32" or not sys.stdin.isatty():
        yield
        return

    fd = sys.stdin.fileno()
    if _posix_depth == 0:
        try:
            _posix_saved_termios = termios.tcgetattr(fd)
            _apply_posix_raw(fd)
        except OSError:
            _posix_saved_termios = None

    _posix_depth += 1
    try:
        yield
    finally:
        _posix_depth -= 1
        if _posix_depth == 0 and _posix_saved_termios is not None:
            try:
                termios.tcsetattr(fd, termios.TCSADRAIN, _posix_saved_termios)
            except OSError:
                pass
            _posix_saved_termios = None


@contextmanager
def pause_keyboard_session():
    """Temporarily restore canonical terminal mode for interactive child TUIs like pomo."""
    if sys.platform == "win32" or not sys.stdin.isatty() or _posix_saved_termios is None:
        yield
        return

    fd = sys.stdin.fileno()
    try:
        termios.tcsetattr(fd, termios.TCSADRAIN, _posix_saved_termios)
    except OSError:
        pass
    try:
        yield
    finally:
        try:
            _apply_posix_raw(fd)
        except OSError:
            pass


def _decode_win_byte(raw: bytes) -> str | None:
    """Decode a Windows msvcrt byte (and extended second byte if needed)."""
    if raw in (b"\x00", b"\xe0"):
        code = msvcrt.getch()
        return _WIN_EXTENDED_MAP.get(code)
    if raw == b"\x03":
        return "CTRL_C"
    if raw in (b"\r", b"\n"):
        return "ENTER"
    if raw == b"\x1b":
        return "ESC"
    if raw in (b"\x08", b"\x7f"):
        return "BACKSPACE"
    if raw == b" ":
        return "SPACE"
    if raw == b"\t":
        return "TAB"
    try:
        return raw.decode("utf-8")
    except (UnicodeDecodeError, ValueError):
        return None


def _posix_has_data(fd: int, timeout: float = 0.0) -> bool:
    readable, _, _ = select.select([fd], [], [], timeout)
    return bool(readable)


def _decode_posix_sequence(read_byte_fn, has_data_fn) -> str | None:
    """Decode a POSIX byte stream into a normalized key token."""
    raw = read_byte_fn()
    if not raw:
        return None
    if raw == b"\x03":
        return "CTRL_C"
    if raw in (b"\r", b"\n"):
        return "ENTER"
    if raw in (b"\x7f", b"\x08"):
        return "BACKSPACE"
    if raw == b" ":
        return "SPACE"
    if raw == b"\t":
        return "TAB"
    if raw == b"\x1b":
        if not has_data_fn(0.03):
            return "ESC"
        b2 = read_byte_fn()
        if b2 == b"[":
            if not has_data_fn(0.02):
                return "ESC"
            seq = bytearray()
            for _ in range(16):
                ch = read_byte_fn()
                seq.extend(ch)
                if 0x40 <= ch[0] <= 0x7E:
                    break
                if not has_data_fn(0.02):
                    break
            if seq == b"3~":
                return "DELETE"
            if seq in (b"1~", b"7~"):
                return "HOME"
            if seq in (b"4~", b"8~"):
                return "END"
            return _ANSI_ARROWS.get(bytes([seq[-1]])) if seq else None
        if b2 == b"O":
            if has_data_fn(0.02):
                return _ANSI_ARROWS.get(read_byte_fn())
            return "ESC"
        return "ESC"

    lead = raw[0]
    if lead >= 0x80:
        if 0xC0 <= lead <= 0xDF:
            extra = 1
        elif 0xE0 <= lead <= 0xEF:
            extra = 2
        elif 0xF0 <= lead <= 0xF7:
            extra = 3
        else:
            extra = 0
        buf = bytearray(raw)
        for _ in range(extra):
            if has_data_fn(0.02):
                buf.extend(read_byte_fn())
        try:
            return buf.decode("utf-8")
        except UnicodeDecodeError:
            return None

    try:
        return raw.decode("utf-8")
    except (UnicodeDecodeError, ValueError):
        return None


def flush_keys(limit: int = 128) -> None:
    """Discard any buffered keystrokes."""
    if sys.platform == "win32":
        for _ in range(limit):
            if not msvcrt.kbhit():
                break
            msvcrt.getch()
    elif sys.stdin.isatty():
        fd = sys.stdin.fileno()
        for _ in range(limit):
            if not _posix_has_data(fd, 0.0):
                break
            os.read(fd, 1)


def read_key_nonblocking() -> str | None:
    """Return a normalized key token if available, otherwise None."""
    if sys.platform == "win32":
        if not msvcrt.kbhit():
            return None
        return _decode_win_byte(msvcrt.getch())

    if not sys.stdin.isatty():
        return None
    fd = sys.stdin.fileno()
    if not _posix_has_data(fd, 0.0):
        return None
    return _decode_posix_sequence(
        lambda: os.read(fd, 1),
        lambda t: _posix_has_data(fd, t),
    )


def read_key(timeout: float | None = None, flush: bool = False) -> str | None:
    """Wait up to `timeout` seconds for a single normalized keypress."""
    with keyboard_session():
        if flush:
            flush_keys()

        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            key = read_key_nonblocking()
            if key is not None:
                return key
            if deadline is not None and time.monotonic() >= deadline:
                return None
            time.sleep(0.02)


@dataclass
class PromptBuffer:
    """Line-editing text buffer with cursor movement and command history."""

    text: str = ""
    cursor: int = 0
    history: list[str] = field(default_factory=list)
    history_idx: int | None = None
    draft: str = ""
    max_len: int = 180

    def handle_key(self, key: str) -> str | None:
        """Process a key token; return submitted text when ENTER is pressed, else None."""
        if key == "ENTER":
            submitted = self.text.strip()
            if submitted and (not self.history or self.history[-1] != submitted):
                self.history.append(submitted)
            self.text = ""
            self.cursor = 0
            self.history_idx = None
            self.draft = ""
            return submitted

        if key == "BACKSPACE":
            if self.cursor > 0:
                self.text = self.text[: self.cursor - 1] + self.text[self.cursor :]
                self.cursor -= 1
            return None

        if key == "DELETE":
            if self.cursor < len(self.text):
                self.text = self.text[: self.cursor] + self.text[self.cursor + 1 :]
            return None

        if key == "LEFT":
            self.cursor = max(0, self.cursor - 1)
            return None

        if key == "RIGHT":
            self.cursor = min(len(self.text), self.cursor + 1)
            return None

        if key == "HOME":
            self.cursor = 0
            return None

        if key == "END":
            self.cursor = len(self.text)
            return None

        if key == "UP":
            if not self.history:
                return None
            if self.history_idx is None:
                self.draft = self.text
                self.history_idx = len(self.history) - 1
            elif self.history_idx > 0:
                self.history_idx -= 1
            self.text = self.history[self.history_idx]
            self.cursor = len(self.text)
            return None

        if key == "DOWN":
            if self.history_idx is None:
                return None
            if self.history_idx < len(self.history) - 1:
                self.history_idx += 1
                self.text = self.history[self.history_idx]
            else:
                self.history_idx = None
                self.text = self.draft
            self.cursor = len(self.text)
            return None

        char = " " if key == "SPACE" else key
        if len(char) == 1 and char.isprintable() and len(self.text) < self.max_len:
            self.text = self.text[: self.cursor] + char + self.text[self.cursor :]
            self.cursor += 1
            self.history_idx = None
        return None
