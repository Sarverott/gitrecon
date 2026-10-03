# Rule

> One function that may conclude one label about one entity.

## What it is

`rule(target, items, thresholds) -> Label | None`. Most rules find the densest [[threshold|window]] of some kind of activity and compare it with a threshold; `bot-like-cadence` measures how evenly spaced events are (coefficient of variation of the gaps).

## Where

`gitrecon/analysis/rules.py` (`ACTOR_RULES`, `REPO_RULES`, `GIST_OWNER_RULES`); helpers in `analysis/timeline.py`. Guide: [[writing-a-label-rule]].

## Relations

Run by the [[labeler]]; tuned by [[threshold]]s; concludes [[label]]s.
