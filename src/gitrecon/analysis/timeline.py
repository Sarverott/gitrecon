"""Time series helpers over timestamped items (events, gists)."""

from __future__ import annotations

import statistics
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class Window(Generic[T]):
    items: list[T]
    start: datetime | None
    end: datetime | None

    def __len__(self) -> int:
        return len(self.items)


def densest_window(
    items: Sequence[T],
    when: Callable[[T], datetime],
    width: timedelta,
    weight: Callable[[T], int] = lambda _: 1,
) -> Window[T]:
    """Window of ``width`` holding the most (weighted) items - two pointers, O(n log n)."""
    ordered = sorted(items, key=when)
    best_lo = best_hi = 0
    best = total = lo = 0
    for hi, item in enumerate(ordered):
        total += weight(item)
        while when(item) - when(ordered[lo]) > width:
            total -= weight(ordered[lo])
            lo += 1
        if total > best:
            best, best_lo, best_hi = total, lo, hi + 1
    chosen = ordered[best_lo:best_hi]
    return Window(chosen, when(chosen[0]) if chosen else None, when(chosen[-1]) if chosen else None)


def gap_variation(times: Sequence[datetime]) -> float | None:
    """Coefficient of variation of gaps between consecutive times.

    Humans are bursty (high CV); schedulers and bots tick evenly (CV near 0).
    """
    ordered = sorted(times)
    gaps = [(b - a).total_seconds() for a, b in zip(ordered, ordered[1:])]
    if len(gaps) < 2:
        return None
    mean = statistics.fmean(gaps)
    if mean == 0:
        return None
    return statistics.pstdev(gaps) / mean
