# GH Archive

> Every public GitHub event since 2011, one gzip file per hour (gharchive.org).

## What it is

The history the Events API does not keep. Hours are named without zero-padding (`2015-01-01-3.json.gz`); recent hours are hundreds of MB. Files are streamed to disk, never held in memory, and kept in their original form - which is also the [[raw-buffer]] format.

## Where

`gitrecon.sources.gharchive`. CLI: `gitrecon archive 2026-10-01-0 2026-10-01-23`.

## Relations

Same record shape as an [[events-feed]]; lands in `data/raw/gharchive/`.
