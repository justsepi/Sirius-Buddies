"""Tests for PromptBuffer line editing, history, POSIX & Windows key decoding."""

from castle.ui.keys import PromptBuffer, _decode_posix_sequence, _decode_win_sequence


def _feed_bytes(seq: bytes):
    it = iter([bytes([b]) for b in seq])
    remaining = [len(seq)]

    def read_fn():
        remaining[0] -= 1
        return next(it)

    def has_data(_timeout: float) -> bool:
        return remaining[0] > 0

    return _decode_posix_sequence(read_fn, has_data)


def _feed_win_chars(seq: str):
    it = iter(seq)
    remaining = [len(seq)]

    def read_fn():
        remaining[0] -= 1
        return next(it)

    def has_data(_timeout: float) -> bool:
        return remaining[0] > 0

    return _decode_win_sequence(read_fn, has_data)


def test_posix_sequence_decoding():
    assert _feed_bytes(b"\x1b[A") == "UP"
    assert _feed_bytes(b"\x1b[B") == "DOWN"
    assert _feed_bytes(b"\x1b[3~") == "DELETE"
    assert _feed_bytes(b"\x1b[5~") == "PGUP"
    assert _feed_bytes(b"\x1b[6~") == "PGDN"
    assert _feed_bytes(b"\x1b[H") == "HOME"
    assert _feed_bytes(b"\x1b[F") == "END"
    assert _feed_bytes(b"\x1b[Z") == "BACKTAB"
    assert _feed_bytes(b"\t") == "TAB"
    assert _feed_bytes(b"\x1b") == "ESC"


def test_windows_scan_codes_and_vt_escape_decoding():
    # Standard msvcrt scan codes
    assert _feed_win_chars("\xe0H") == "UP"
    assert _feed_win_chars("\xe0P") == "DOWN"
    assert _feed_win_chars("\x00K") == "LEFT"
    assert _feed_win_chars("\xe0M") == "RIGHT"
    assert _feed_win_chars("\xe0S") == "DELETE"
    assert _feed_win_chars("\r") == "ENTER"

    # Windows Terminal VT-mode escape sequences
    assert _feed_win_chars("\x1b[A") == "UP"
    assert _feed_win_chars("\x1b[B") == "DOWN"
    assert _feed_win_chars("\x1b[Z") == "BACKTAB"
    assert _feed_win_chars("\x1b") == "ESC"


def test_prompt_buffer_editing_and_history():
    buf = PromptBuffer()
    for ch in ("h", "i"):
        assert buf.handle_key(ch) is None
    assert buf.text == "hi"
    assert buf.handle_key("ENTER") == "hi"
    assert buf.text == ""
    assert buf.history == ["hi"]

    for ch in ("a", "c"):
        buf.handle_key(ch)
    buf.handle_key("LEFT")
    buf.handle_key("b")
    assert buf.text == "abc"
    buf.handle_key("HOME")
    buf.handle_key("DELETE")
    assert buf.text == "bc"
    buf.handle_key("END")
    buf.handle_key("BACKSPACE")
    assert buf.text == "b"

    buf.handle_key("UP")
    assert buf.text == "hi"
    buf.handle_key("DOWN")
    assert buf.text == "b"
