# News feed

> An RSS 2.0, Atom or RDF feed - blogs, changelogs, advisories, releases, exploit lists.

## What it is

Polled with `If-None-Match` / `If-Modified-Since`; items already seen are skipped; each item is normalized to a `FeedItem` (id, title, link, dates, summary as plain text, authors, categories). XML from outside is parsed with `defusedxml`.

## Where

`gitrecon.sources.feeds` (`FeedReader`, `parse_feed`), `gitrecon.models.FeedItem`; state in `data/state/feeds.json`. CLI: `gitrecon feeds [URL...] --items --save`.

## Relations

URLs come from the [[link-catalog]] or from a [[blog-article]]'s page (feed discovery). Not to be confused with an [[events-feed]].
