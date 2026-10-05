"""History as music: notes from commits, tablature, ABC, MIDI."""

import json
import struct

from test_gitgraph import Repo  # the throwaway-repository helper

from gitrecon.main import main
from gitrecon.mapping import score
from gitrecon.mapping.gitgraph import Commit


def commit(sha, lane, time, parents=(), subject="feat: x", tags=()):
    return Commit(sha * 40, [p * 40 for p in parents], time, "t", subject, list(tags), lane)


HOUR, DAY = 3600, 86400
HISTORY = [
    commit("0", "master", 0),                                              # fret 0, then 10 minutes
    commit("1", "master", 600),                                            # fret 3, then 2 hours
    commit("a", "development", 600 + 2 * HOUR, parents=["1"]),             # string 1, fret 0 (a=10 -> step 0)
    commit("2", "development", 600 + 2 * HOUR + 3 * DAY, parents=["a"], subject='Revert "feat: x"'),
    commit("3", "master", 600 + 2 * HOUR + 20 * DAY, parents=["1", "a"], subject="Merge branch", tags=["v1.0.0"]),
]


def test_notes_strings_frets_lengths():
    notes = score.score_notes(HISTORY)
    assert [(n.string, n.frets, n.eighths) for n in notes] == [
        (0, {0: 0}, 1), (0, {0: 3}, 2), (1, {1: 0}, 4), (1, {}, 8),        # the revert is a rest
        (0, {0: 7, 1: 0}, 4)]                                             # the merge: a chord with development's note
    assert notes[4].tag == "v1.0.0" and notes[4].pitches == [45, 47]      # A2 (open A string) and B2
    assert notes[0].pitches == [40]                                       # the low E string, open


def test_tab_has_six_strings_and_marks_the_rest():
    tab = score.to_tab(score.score_notes(HISTORY))
    lines = tab.splitlines()
    assert [line[:2] for line in lines] == ["e|", "B|", "G|", "D|", "A|", "E|"]
    assert lines[5] == "E|0-3----------------7----|" and lines[4] == "A|-----0----x--------0----|"
    assert len({len(line) for line in lines}) == 1
    wide = score.to_tab(score.score_notes([commit("4", "master", n) for n in range(60)]), width=40)
    assert wide.count("\n\n") >= 2 and all(len(line) <= 40 for line in wide.splitlines())
    assert "10-" in wide                                                   # two-digit frets keep their own cell


def test_abc_and_midi():
    notes = score.score_notes(HISTORY)
    abc = score.to_abc(notes, title="demo")
    assert abc.splitlines()[:2] == ["X:1", "T:demo"] and "K:Em" in abc
    assert abc.splitlines()[-1] == 'E,, G,,2 A,,4 z8 | "^v1.0.0"[A,,B,,]4 |'
    midi = score.to_midi(notes)
    assert midi[:4] == b"MThd" and struct.unpack(">IHHH", midi[4:14]) == (6, 0, 1, 480)
    length = struct.unpack(">I", midi[18:22])[0]
    assert midi[14:18] == b"MTrk" and len(midi) == 22 + length and midi.endswith(b"\xff\x2f\x00")
    assert midi.count(b"\x90") >= 5                                        # five sounding pitches (one chord of two)
    assert score._varlen(0) == b"\x00" and score._varlen(480) == b"\x83\x60"


def test_score_command(tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("GITRECON_DATA", str(tmp_path / "data"))
    repo = Repo(tmp_path / "song")
    for n in range(4):
        repo.commit(f"feat: {n}")
    assert main(["score", str(repo.path)]) == 0
    assert capsys.readouterr().out.startswith("e|")
    assert main(["score", str(repo.path), "--format", "abc", "--save", "--json"]) == 0
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert len(data["notes"]) == 4 and data["score"].startswith("X:1")
    assert (tmp_path / "data" / "scores" / "song.abc").read_text() == data["score"]
    assert main(["score", str(repo.path), "--format", "midi"]) == 0
    assert (tmp_path / "data" / "scores" / "song.mid").read_bytes()[:4] == b"MThd"


def test_contributors_band_mode(tmp_path, capsys, monkeypatch):
    history = [commit("0", "master", 0), commit("1", "master", 600), commit("5", "master", 1200),
               commit("a", "development", 1800, parents=["5"])]
    for item, author in zip(history, ["Ann", "Bob", "Ann", "Ann"]):
        item.author = author
    notes = score.score_notes(history)
    assert score.band(notes) == [
        {"author": "Ann", "notes": 3, "program": 25, "instrument": "steel guitar"},     # the busiest plays guitar
        {"author": "Bob", "notes": 1, "program": 32, "instrument": "acoustic bass"}]

    tab = score.to_tab(notes, band_mode=True)
    assert tab.splitlines()[0] == " |1 2 1 1" and tab.splitlines()[1].startswith("e|")
    assert tab.splitlines()[-2:] == ["1 = Ann (steel guitar, 3 notes)", "2 = Bob (acoustic bass, 1 notes)"]

    abc = score.to_abc(notes, band_mode=True)
    assert 'V:1 name="Ann" clef=treble-8' in abc and "%%MIDI program 32" in abc
    voices = abc.split("V:1\n")[1].split("V:2\n")
    assert voices[0].splitlines()[1] == "E,, z E,, A,,4 |" and voices[1].splitlines()[1] == "z G,, z z4 |"  # Bob rests while Ann plays

    midi = score.to_midi(notes, band_mode=True)
    assert struct.unpack(">IHHH", midi[4:14]) == (6, 1, 3, 480)             # format 1: tempo track + one per contributor
    assert midi.count(b"MTrk") == 3 and b"Ann (steel guitar)" in midi and b"\xc1\x20" in midi   # channel 2: program 32
    assert score.to_midi(notes)[:14] == b"MThd" + struct.pack(">IHHH", 6, 0, 1, 480)             # the default is unchanged

    monkeypatch.setenv("GITRECON_DATA", str(tmp_path / "data"))
    repo = Repo(tmp_path / "band")
    repo.commit("feat: 1")
    assert main(["score", str(repo.path), "--format", "midi", "--contributors-band-mode"]) == 0
    assert "1 contributors: t (steel guitar)" in capsys.readouterr().out
    assert (tmp_path / "data" / "scores" / "band-band.mid").read_bytes()[8:10] == b"\x00\x01"
