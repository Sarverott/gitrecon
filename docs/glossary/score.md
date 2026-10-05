# Score

> A repository's history as music: guitar tablature, ABC notation, a MIDI file.

## What it is

The same commits-with-lanes the [[git-graph]] draws, read as a score:

| In git | In the score |
| --- | --- |
| lane | a guitar string, the main lane lowest (E A D G B e; a seventh lane starts over) |
| commit | a note; its fret is a step of the minor pentatonic scale (0, 3, 5, 7, 10) picked by the first digit of the commit's hash |
| pause before the next commit | length: under an hour an eighth, under a day a quarter, under a week a half, longer a whole note |
| merge | a chord with the last note of the lane merged in |
| revert | a rest |
| tag | an accent (and a text mark in ABC) |

The same history always plays the same tune.

## Where

`gitrecon.mapping.score` (`score_notes`, `to_tab`, `to_abc`, `to_midi`). CLI:
`gitrecon score [PATH] [--format tab|abc|midi] [--max-commits N] [--tempo N] [--save]`.

> **Remember!** `--format midi` always writes a file, `data/scores/<repository>.mid`;
> `--save` writes the tab or ABC next to it. Both are in gitrecon's data folder.

## Relations

Built on [[git-graph]]'s lanes.
