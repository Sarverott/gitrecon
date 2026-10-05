# Git graph

> A repository's history across all branches, drawn as a Mermaid `gitGraph`.

## What it is

Every branch (local and remote) claims the commits along its first-parent chain, in priority
order (`master`/`main`, then the BOS loop branches, then the rest) - that is a commit's
*lane*. Commits that came in only through the merge of a branch that is gone get a lane named
after the merge message. Commits are replayed parents first; a lane opens right after the
commit it starts from; a merge commit becomes `merge`.

Limits of the Mermaid format: one root, a merge takes one other branch, and it is drawn from
that branch's current head. `--max-commits` draws the newest N (default 150).

## Where

`gitrecon.mapping.gitgraph` (`read_history`, `assign_lanes`, `render_gitgraph`, `git_graph`).
CLI: `gitrecon gitgraph [PATH] [--format mermaid] [--max-commits N] [--labels] [--save]`.

> **Remember!** `--save` writes to `data/gitgraphs/<repository>.md` in gitrecon's data folder
> (`GITRECON_DATA`), not into the repository you are looking at.

## Relations

A sibling of the [[network]] diagrams; shows the [[craft-loop]] of a repository at a glance.
