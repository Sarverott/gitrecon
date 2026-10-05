"""A repository's history as music: guitar tablature, ABC notation, a MIDI file.

    notes = score_notes(commits)            # commits with lanes, see gitgraph.assign_lanes
    print(to_tab(notes))

A gitGraph already has what a score has - parallel lines, events in time order, lines
meeting. The reading, with no decision left to a musician:

- **lane -> string.** The main lane is the lowest string of a guitar in standard tuning
  (E2 A2 D3 G3 B3 E4); a seventh lane starts again on the lowest string.
- **commit -> note.** The fret comes from the commit itself: the first hexadecimal digit of
  its hash picks a step of the minor pentatonic scale (frets 0, 3, 5, 7, 10), so the same
  history always plays the same tune and stays in one key per string.
- **time -> length.** The pause before the next commit: under an hour an eighth, under a day
  a quarter, under a week a half, longer a whole note.
- **merge -> chord** of the merging lane's note and the last note of the lane merged in.
- **revert -> rest.** **tag -> accent** (and a text mark in ABC).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

from gitrecon.mapping.gitgraph import Commit

STRINGS = [40, 45, 50, 55, 59, 64]  # MIDI pitches of E2 A2 D3 G3 B3 E4, lowest first
STRING_NAMES = ["E", "A", "D", "G", "B", "e"]
PENTATONIC = [0, 3, 5, 7, 10]  # frets of the minor pentatonic scale on one string
HOUR, DAY, WEEK = 3600, 86400, 604800
GUITAR = 25  # General MIDI program: acoustic guitar (steel)


@dataclass
class Note:
    sha: str
    lane: str
    string: int  # 0 = lowest
    frets: dict[int, int] = field(default_factory=dict)  # string -> fret; two entries: a chord; none: a rest
    eighths: int = 2  # length in eighth notes: 1, 2, 4 or 8
    tag: str | None = None

    @property
    def pitches(self) -> list[int]:
        return sorted(STRINGS[s] + fret for s, fret in self.frets.items())


def _length(seconds: int) -> int:
    return 1 if seconds < HOUR else 2 if seconds < DAY else 4 if seconds < WEEK else 8


def score_notes(commits: list[Commit]) -> list[Note]:
    """One note per commit, in the order given (parents first, as ``read_history`` returns them)."""
    lanes: list[str] = []
    for commit in commits:
        if commit.lane not in lanes:
            lanes.append(commit.lane)
    by_sha = {c.sha: c for c in commits}
    last: dict[str, tuple[int, int]] = {}  # lane -> (string, fret) of its last note
    notes = []
    for index, commit in enumerate(commits):
        string = lanes.index(commit.lane) % len(STRINGS)
        fret = PENTATONIC[int(commit.sha[0], 16) % len(PENTATONIC)]
        gap = commits[index + 1].time - commit.time if index + 1 < len(commits) else DAY
        note = Note(commit.sha, commit.lane, string, {string: fret}, _length(max(gap, 0)),
                    commit.tags[0] if commit.tags else None)
        if commit.subject.startswith("Revert"):
            note.frets = {}
        else:
            for parent in commit.parents[1:]:
                other = by_sha.get(parent)
                if other and other.lane in last and last[other.lane][0] != string:
                    note.frets[last[other.lane][0]] = last[other.lane][1]
                    break
            last[commit.lane] = (string, fret)
        notes.append(note)
    return notes


# --- tablature ----------------------------------------------------------------------------


def to_tab(notes: list[Note], width: int = 96) -> str:
    """ASCII guitar tablature, highest string on top; a note's width follows its length."""
    rows = [f"{name}|" for name in STRING_NAMES]
    blocks: list[list[str]] = []
    current = [row for row in rows]
    for note in notes:
        cell = max(1 + note.eighths, 1 + max((len(str(fret)) for fret in note.frets.values()), default=1))
        column = []
        for string in range(len(STRINGS)):
            text = str(note.frets[string]) if string in note.frets else ("x" if not note.frets and string == note.string else "")
            column.append(text.ljust(cell, "-") if text else "-" * cell)
        if len(current[0]) + cell + 1 > width:
            blocks.append([row + "|" for row in current])
            current = [row for row in rows]
        current = [row + part for row, part in zip(current, column)]
    blocks.append([row + "|" for row in current])
    return "\n\n".join("\n".join(reversed(block)) for block in blocks) + "\n"


# --- ABC notation -----------------------------------------------------------------------------

_ABC_NAMES = ["C", "^C", "D", "^D", "E", "F", "^F", "G", "^G", "A", "^A", "B"]


def _abc_pitch(midi: int) -> str:
    name, octave = _ABC_NAMES[midi % 12], midi // 12 - 1  # MIDI 60 = C4 = "C" in ABC
    if octave >= 5:
        return name.lower() + "'" * (octave - 5)
    return name + "," * (4 - octave)


def to_abc(notes: list[Note], title: str = "git history") -> str:
    """ABC notation (abcjs, abc2midi, EasyABC ... render and play it); sounds an octave lower on a guitar."""
    lines = ["X:1", f"T:{title}", "C:gitrecon", "M:4/4", "L:1/8", "Q:1/4=96", "K:Em clef=treble-8"]
    bar, filled, bars = [], 0, []
    for note in notes:
        length = "" if note.eighths == 1 else str(note.eighths)
        pitches = [_abc_pitch(p) for p in dict.fromkeys(note.pitches)]
        text = "z" if not pitches else pitches[0] if len(pitches) == 1 else "[" + "".join(pitches) + "]"
        mark = f'"^{note.tag}"' if note.tag else ""
        bar.append(f"{mark}{text}{length}")
        filled += note.eighths
        if filled >= 8:
            bars.append(" ".join(bar))
            bar, filled = [], 0
    if bar:
        bars.append(" ".join(bar))
    for start in range(0, len(bars), 4):
        lines.append(" | ".join(bars[start:start + 4]) + " |")
    return "\n".join(lines) + "\n"


# --- MIDI -----------------------------------------------------------------------------------


def _varlen(value: int) -> bytes:
    out = [value & 0x7F]
    while value := value >> 7:
        out.append((value & 0x7F) | 0x80)
    return bytes(reversed(out))


def to_midi(notes: list[Note], tempo: int = 96, ticks: int = 480) -> bytes:
    """A standard MIDI file (format 0, one track, steel guitar)."""
    eighth = ticks // 2
    track = bytearray()
    track += b"\x00\xff\x51\x03" + struct.pack(">I", 60_000_000 // tempo)[1:]  # tempo
    track += b"\x00" + bytes([0xC0, GUITAR])
    rest = 0
    for note in notes:
        duration = note.eighths * eighth
        pitches = note.pitches
        if not pitches:
            rest += duration
            continue
        velocity = 112 if note.tag else 84
        for index, pitch in enumerate(pitches):
            track += _varlen(rest if index == 0 else 0) + bytes([0x90, pitch, velocity])
        for index, pitch in enumerate(pitches):
            track += _varlen(duration if index == 0 else 0) + bytes([0x80, pitch, 0])
        rest = 0
    track += _varlen(rest) + b"\xff\x2f\x00"
    return b"MThd" + struct.pack(">IHHH", 6, 0, 1, ticks) + b"MTrk" + struct.pack(">I", len(track)) + bytes(track)
