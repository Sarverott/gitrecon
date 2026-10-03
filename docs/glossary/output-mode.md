# Output mode

> How a command prints: readable text, `--json` for programs, or `--urls` for addresses.

## What it is

Every listing command prints text by default. `--json` puts only data on stdout (a list, an
object, or JSON Lines for streams like `events --watch`); `--urls` puts only web addresses on
stdout, one per line, deduplicated. In both machine modes, notes and summaries go to stderr.
The item shapes are the models' `to_json()`; addresses are their `html_url` (bots link to
`github.com/apps/<name>`).

## Where

`gitrecon.cli.output` (`Output`, `add_output_flags`); `Entity.html_url`, `Entity.to_json()`,
`url_for_key()` in `gitrecon.models.base`. Guide: [[integration]].

## Relations

Applies to listings of every [[entity]], [[label]], [[link-catalog]], [[news-feed]] items,
[[rfc-index]] entries and [[blog-article]]s; `events --json` streams [[event]]s.
