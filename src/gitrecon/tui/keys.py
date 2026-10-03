"""Reading single key presses from the terminal (arrows, enter, escape, letters)."""

from __future__ import annotations

import os
import sys

UP, DOWN, LEFT, RIGHT = "up", "down", "left", "right"
PAGE_UP, PAGE_DOWN, HOME, END = "page-up", "page-down", "home", "end"
ENTER, ESCAPE, BACKSPACE, TAB, SPACE = "enter", "escape", "backspace", "tab", "space"

ESCAPE_SEQUENCES = {
    "[A": UP, "[B": DOWN, "[C": RIGHT, "[D": LEFT,
    "OA": UP, "OB": DOWN, "OC": RIGHT, "OD": LEFT,
    "[5~": PAGE_UP, "[6~": PAGE_DOWN,
    "[H": HOME, "[F": END, "[1~": HOME, "[4~": END, "OH": HOME, "OF": END,
}


def decode(data: bytes) -> str:
    """Raw bytes of one key press -> a key name, or the typed character."""
    if data in (b"\r", b"\n"):
        return ENTER
    if data in (b"\x7f", b"\x08"):
        return BACKSPACE
    if data == b"\t":
        return TAB
    if data == b" ":
        return SPACE
    if data == b"\x03":
        raise KeyboardInterrupt
    if data.startswith(b"\x1b"):
        if len(data) == 1:
            return ESCAPE
        return ESCAPE_SEQUENCES.get(data[1:].decode(errors="ignore"), ESCAPE)
    return data.decode(errors="ignore")


def read_key() -> str:
    """Block until one key is pressed (POSIX terminals; Windows through msvcrt)."""
    if os.name == "nt":  # pragma: no cover - not exercised on Linux CI
        import msvcrt

        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):
            return {"H": UP, "P": DOWN, "K": LEFT, "M": RIGHT, "I": PAGE_UP, "Q": PAGE_DOWN,
                    "G": HOME, "O": END}.get(msvcrt.getwch(), ESCAPE)
        return decode(ch.encode())

    import select
    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        data = os.read(fd, 1)
        if data == b"\x1b":
            # the rest of an escape sequence arrives at once; a lone ESC does not
            while select.select([fd], [], [], 0.03)[0]:
                data += os.read(fd, 1)
                if len(data) >= 6:
                    break
        return decode(data)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
