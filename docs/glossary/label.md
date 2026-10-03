# Label

> A conclusion about an entity: what is happening, how sure, and why.

## What it is

Name, target (an [[entity]] key), confidence (0.5 at the threshold, towards 1.0 above it), evidence (event or gist ids) and details. Current labels: `declared-bot`, `burst`, `bot-like-cadence`, `push-flood`, `repo-spree`, `mass-forker`, `fork-wave`, `star-burst`, `mass-gist-drop`.

## Where

`gitrecon.models.Label`. CLI: `gitrecon label [--json]`.

## Relations

Concluded by a [[rule]] run by the [[labeler]]; can be summarized into a [[digest]].
