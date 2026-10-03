# Craft loop

> The branch loop every change travels: development -> revision -> testing -> releasing -> master.

## What it is

One pull request per step, opened automatically; steps merge on their own when their checks pass and the config allows it. Every pass through `master` is a release: version bump, changelog, tag, wheel and sdist on a GitHub Release, and a back-merge PR into `development`. `rejection` is the way back.

## Where

`.github/bos.config.json`, `.github/bos/flow.py`, `.github/workflows/`. `task gh:loop` shows how it resolves. Guide: [[committing-and-releasing]].

## Relations

Uses [[metadata-sync]]; commits go through [[routine]]s.
