# Metadata sync

> One place for the project's name, version, description, authors and tags: `metadata.json`.

## What it is

Copied into `package.json`, `pyproject.toml` and the lockfiles before every commit, and checked in pull requests. Never edit the version by hand - the release does it.

## Where

`scripts/sync_metadata.py`; `task sync`, `task scripts:sync:check`.

## Relations

Part of the [[craft-loop]]'s checks.
