# Entity

> Anything gitrecon can map, with a kind and a stable key.

## What it is

Keys look like `user:octocat`, `org:github`, `repo:owner/name`, `gist:<id>`, `project:owner/3`, `star:user->owner/name`. Keys are lowercase, so the same account seen in different spellings is one node. Models: `User`, `Organization`, `Repository`, `Gist`, `Project`, `Event`, `Star`, `RFC`, `FeedItem`, `BlogArticle` - one class per file in `src/gitrecon/models/`.

## Where

`gitrecon.models.base.Entity`; every model has `from_api()` and `to_dict()`.

## Relations

Nodes of the [[activity-graph]]; targets of a [[label]].
