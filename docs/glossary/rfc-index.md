# RFC index

> The RFC Editor's list of every Request for Comments, parsed into records.

## What it is

Number, title, authors, date, status (`PROPOSED STANDARD`, ...), formats, DOI and relations (obsoletes, obsoleted by, updates, updated by, also). Handles today's format: numbers are not zero-padded and RFCs above 9999 exist.

## Where

`gitrecon.sources.rfc_index`, `gitrecon.models.RFC`. CLI: `gitrecon rfc --search quic`, `--number 2026`, `--save` (`data/catalog/rfc-index.jsonl`).

## Relations

Ported from a [[gist]] notebook. A reference set for protocol-related repositories.
