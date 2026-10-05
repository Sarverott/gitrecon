# Contributor

> Who made a repository, read from its git log.

## What it is

Per person: commits and merges, lines added and deleted, the first and the last day, and
how often others named them in `Co-authored-by`. One person under several names or
addresses is one contributor: git's `.mailmap` is honoured, and records sharing an address
or a name are joined.

An **ignorelist** is a text file of identities to leave out - a name or an address per
line, `*` and `?` as wildcards. With `--ignorelist` they are not listed, not credited in the
AUTHORS text, not drawn in the pie, and in `gitrecon score` their commits are silent and they
get no instrument. The default list, `resources/ignorelist.txt`, holds bots.

## Where

`gitrecon.mapping.contributors` (`contributors`, `read_ignorelist`, `is_ignored`,
`authors_text`, `contributors_pie`, `pie`). CLI: `gitrecon contributors [PATH]
[--format list|authors|pie] [--by commits|lines|added] [--ignorelist [FILE]] [--save]`.

> **Remember!** `--save` writes `data/contributors/<repository>.AUTHORS` (or
> `<repository>-<by>.md` for the pie) in gitrecon's data folder - not an `AUTHORS` file in the
> repository. To make one: `gitrecon contributors --ignorelist --format authors > AUTHORS`.

## Relations

Feeds the band of the [[score]]; counts the same commits [[humanish]] reads.
