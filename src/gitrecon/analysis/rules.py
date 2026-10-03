"""Deterministic labeling rules.

Each rule takes one entity's activity and returns a :class:`Label` or ``None``.
Confidence grows with how far the observation exceeds the threshold.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta

from gitrecon.analysis.timeline import densest_window, gap_variation
from gitrecon.models import Event, Gist, Label


@dataclass
class Thresholds:
    window: timedelta = timedelta(hours=1)
    burst_events: int = 100
    cadence_min_events: int = 20
    cadence_max_variation: float = 0.15
    push_flood_commits: int = 500
    repo_spree: int = 10
    mass_forks_by_actor: int = 20
    fork_wave: int = 20
    star_burst: int = 50
    gist_drop: int = 10


def _confidence(observed: float, threshold: float) -> float:
    """0.5 at the threshold, approaching 1.0 as observed grows."""
    if threshold <= 0:
        return 1.0
    return round(min(1.0, 0.5 + 0.5 * (observed - threshold) / threshold), 2)


def _window_label(name, target, window, threshold, **details) -> Label | None:
    observed = len(window) if "observed" not in details else details.pop("observed")
    if observed < threshold:
        return None
    return Label(
        name=name,
        target=target,
        confidence=_confidence(observed, threshold),
        evidence=[item.id for item in window.items],
        details={
            "observed": observed,
            "threshold": threshold,
            "from": window.start.isoformat() if window.start else None,
            "to": window.end.isoformat() if window.end else None,
            **details,
        },
    )


def _when(e: Event | Gist):
    return e.created_at


# --- actor rules -----------------------------------------------------------


def declared_bot(target: str, events: Sequence[Event], t: Thresholds) -> Label | None:
    actor = events[0].actor if events else None
    if actor and actor.is_bot:
        return Label("declared-bot", target, 1.0, [events[0].id], {"login": actor.login})
    return None


def burst(target: str, events: Sequence[Event], t: Thresholds) -> Label | None:
    return _window_label("burst", target, densest_window(events, _when, t.window), t.burst_events)


def bot_like_cadence(target: str, events: Sequence[Event], t: Thresholds) -> Label | None:
    if len(events) < t.cadence_min_events:
        return None
    variation = gap_variation([e.created_at for e in events])
    if variation is None or variation > t.cadence_max_variation:
        return None
    confidence = round(1.0 - 0.5 * variation / t.cadence_max_variation, 2)
    return Label(
        "bot-like-cadence",
        target,
        confidence,
        [e.id for e in events],
        {"gap_variation": round(variation, 4), "events": len(events)},
    )


def push_flood(target: str, events: Sequence[Event], t: Thresholds) -> Label | None:
    pushes = [e for e in events if e.type == "PushEvent"]
    window = densest_window(pushes, _when, t.window, weight=lambda e: e.commit_count)
    commits = sum(e.commit_count for e in window.items)
    return _window_label("push-flood", target, window, t.push_flood_commits, observed=commits)


def repo_spree(target: str, events: Sequence[Event], t: Thresholds) -> Label | None:
    created = [
        e for e in events if e.type == "CreateEvent" and e.payload.get("ref_type") == "repository"
    ]
    return _window_label("repo-spree", target, densest_window(created, _when, t.window), t.repo_spree)


def mass_forker(target: str, events: Sequence[Event], t: Thresholds) -> Label | None:
    forks = [e for e in events if e.type == "ForkEvent"]
    return _window_label(
        "mass-forker", target, densest_window(forks, _when, t.window), t.mass_forks_by_actor
    )


# --- repository rules ------------------------------------------------------


def fork_wave(target: str, events: Sequence[Event], t: Thresholds) -> Label | None:
    forks = [e for e in events if e.type == "ForkEvent"]
    window = densest_window(forks, _when, t.window)
    actors = {e.actor.login for e in window.items if e.actor}
    return _window_label("fork-wave", target, window, t.fork_wave, distinct_actors=len(actors))


def star_burst(target: str, events: Sequence[Event], t: Thresholds) -> Label | None:
    # WatchEvent is what GitHub emits for starring.
    stars = [e for e in events if e.type == "WatchEvent"]
    window = densest_window(stars, _when, t.window)
    actors = {e.actor.login for e in window.items if e.actor}
    return _window_label("star-burst", target, window, t.star_burst, distinct_actors=len(actors))


# --- gist rules ------------------------------------------------------------


def mass_gist_drop(target: str, gists: Sequence[Gist], t: Thresholds) -> Label | None:
    window = densest_window(gists, _when, t.window)
    languages = sorted({lang for g in window.items for lang in g.languages})
    return _window_label("mass-gist-drop", target, window, t.gist_drop, languages=languages)


ACTOR_RULES = [declared_bot, burst, bot_like_cadence, push_flood, repo_spree, mass_forker]
REPO_RULES = [fork_wave, star_burst]
GIST_OWNER_RULES = [mass_gist_drop]
