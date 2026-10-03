# Events feed

> An Events API endpoint gitrecon listens to: public, a user, an organization or a repository.

## What it is

`public`, `user:NAME`, `org:NAME`, `repo:OWNER/NAME`. GitHub keeps only the latest 300 events (90 days at most) per feed, so a feed is *polled*: conditional requests with `If-None-Match` (a `304` costs no rate limit), at the interval GitHub asks for in `X-Poll-Interval`. Seen event ids are remembered so overlapping pages are not stored twice.

## Where

`gitrecon.sources.events` (`Feed`, `EventPoller`); state in `data/state/feed-*.json`. CLI: `gitrecon events org:github [--watch]`, `task listen -- org:github`.

## Relations

Produces [[event]]s into the [[raw-buffer]]. Not to be confused with a [[news-feed]] (RSS/Atom).
