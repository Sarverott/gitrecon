# Activity graph

> Who touches what: entities as nodes, observed relations as edges with evidence.

## What it is

Edges are named after the event (`PushEvent`, `WatchEvent`, ...) or the relation (`owned_by`, `belongs_to`, `active_in`, `forked_to`, `member_of`, `created_gist`). Every edge keeps the ids of the events that show it. The summary lists node kinds, relations and *hubs* (most connected nodes).

## Where

`gitrecon.mapping.ActivityGraph`. CLI: `gitrecon map [--node user:octocat] [--full]`.

## Relations

Built from the [[raw-buffer]]; nodes are [[entity|entities]]. Not the same as the [[atlas]] (the shared map dataset).
