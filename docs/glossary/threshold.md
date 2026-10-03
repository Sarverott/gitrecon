# Threshold

> The numbers a rule compares against, including the time window.

## What it is

A dataclass of plain fields: `window` (default 1 hour), `burst_events`, `push_flood_commits`, `repo_spree`, `fork_wave`, `star_burst`, `gist_drop`, `cadence_max_variation`, ...

## Where

`gitrecon.analysis.Thresholds`; `Labeler(thresholds=Thresholds(burst_events=50))`.

## Relations

Tunes every [[rule]].
