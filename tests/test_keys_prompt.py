"""Tests for PromptBuffer line editing, history, and POSIX sequence decoding."""

from mansion.ui.keys import PromptBuffer, _decode_posix_sequence


def _feed_bytes(seq: bytes):
    it = iter([bytes([b]) for b in seq])
    remaining = [len(seq)]

    def read_fn():
        remaining[0] -= 1
        return next(it)

    def has_data(_timeout: float) -> bool:
        return remaining[0] > 0

    return _decode_posix_sequence(read_fn, has_data)


def test_posix_sequence_decoding():
    assert _feed_bytes(b"\x1b[A") == "UP"
    assert _feed_bytes(b"\x1b[B") == "DOWN"
    assert _feed_bytes(b"\x1b[3~") == "DELETE"
    assert _feed_bytes(b"\x1b[H") == "HOME"
    assert _feed_bytes(b"\x1b[F") == "END"
    assert _feed_bytes(b"\t") == "TAB"
    assert _feed_bytes(b"\x1b") == "ESC"


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

    # Recall history with UP then return to draft with DOWN
    buf.handle_key("UP")
    assert buf.text == "hi"
    buf.handle_key("DOWN")
    assert buf.text == "b"
