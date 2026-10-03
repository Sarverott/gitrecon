# Identity

> One account, profile or address of someone on one platform.

## What it is

`{"user", "platform", "type": "profile" | "mail" | ..., "sibiling": [...], "description"}`. Identities of the same person point at each other in `sibiling` (spelled as in the dataset README), e.g. a GitHub profile and the same account's gists.

## Where

`gitrecon.atlas.namespace.Identity`; `UserNamespace.add()`, `link()`, `flush()`.

## Relations

Lives in the [[user-namespace]].
