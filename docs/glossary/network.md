# Network

> Repositories, users and organizations around one user, as a graph of relations.

## What it is

`member_of` (user → organization), `owned_by` (repository → owner) and `fork_of`
(repository → its upstream, whose owner joins the graph). Drawn at two zoom levels:
**owners** - who forks from whom, with counts - and **repos**, grouped by owner. Listings
come from REST; fork parents from GraphQL. Where GraphQL hides an upstream (it sits in an
organization refusing the token), REST is asked instead; an organization refusing the whole
query is listed under "not seen" in the summary (`notes` in JSON).

## Where

`gitrecon.mapping.network` (`collect_network`, `owner_network`), `gitrecon.mapping.render`
(Mermaid, DOT, JSON). CLI: `gitrecon network USER [--format mermaid|dot] [--level owners|repos]
[--save]`.

> **Remember!** `--save` writes the diagram to `data/networks/<user>-<level>.md` in gitrecon's data
> folder (`GITRECON_DATA`), not to the folder you run the command from. The repos level of a big
> account is hundreds of lines - open the saved file in Obsidian or on GitHub rather than reading
> it in the terminal.

## Relations

Uses the same structure as the [[activity-graph]]; nodes are [[entity|entities]]; printed in
every [[output-mode]].
