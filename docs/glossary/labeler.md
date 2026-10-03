# Labeler

> Groups activity per entity and runs every rule over it.

## What it is

Events are grouped per actor and per repository, gists per owner; each group goes through its rule set. Labels come out sorted by confidence.

## Where

`gitrecon.analysis.Labeler`.

## Relations

Runs [[rule]]s with [[threshold]]s over the [[raw-buffer]]; produces [[label]]s.
