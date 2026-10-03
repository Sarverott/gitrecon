# Event

> One thing that happened on GitHub: a push, a star, a fork, an issue...

## What it is

A record of the Events API or GH Archive: `id`, `type` (`PushEvent`, `WatchEvent`, `ForkEvent`, ...), `actor`, `repo`, optional `org`, `payload`, `created_at`. Events are the raw material of the [[activity-graph]] and of [[label]]s.

## Where

`gitrecon.models.Event` (`models/event.py`); `Event.from_api(record)`.

## Relations

Collected by an [[events-feed]] or from [[gh-archive]]; kept in the [[raw-buffer]]. Its `actor` is a user, its `repo` a repository, see [[entity]].
