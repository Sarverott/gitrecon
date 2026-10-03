# Raw buffer

> Append-only store of everything collected: gzip JSONL partitioned by source and UTC hour.

## What it is

`data/raw/<source>/<YYYY-MM-DD>/<HH>[-<suffix>].json.gz`. Records are never rewritten; mapping and analysis are always rebuilt from here, so rules can change and be re-run over history. Same format as [[gh-archive]], so archive hours drop in unchanged and DuckDB can read it all at once.

## Where

`gitrecon.storage.RawBuffer`. CLI: `gitrecon status`. Location: `GITRECON_DATA` (default `data/`).

## Relations

Fed by [[events-feed]]s, [[gh-archive]], [[star]]s, [[gist]]s, [[news-feed]]s, [[blog-article]]s; read by the [[activity-graph]] and the [[labeler]].
