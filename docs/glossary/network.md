# Network

> Repositories, users and organizations around one user, as a graph of relations.

## What it is

`member_of` (user → organization), `owned_by` (repository → owner) and `fork_of`
(repository → its upstream, whose owner joins the graph). Drawn at two zoom levels:
**owners** - who forks from whom, with counts - and **repos**, grouped by owner. Listings
come from REST; fork parents from GraphQL, which may answer partly when an organization
refuses the token.

## Where

`gitrecon.mapping.network` (`collect_network`, `owner_network`), `gitrecon.mapping.render`
(Mermaid, DOT, JSON). CLI: `gitrecon network USER [--format mermaid|dot] [--level owners|repos]
[--save]`; diagrams land in `data/networks/`.

## Relations

Uses the same structure as the [[activity-graph]]; nodes are [[entity|entities]]; printed in
every [[output-mode]].
