# Writing a label rule

A [[rule]] is one function in `src/gitrecon/analysis/rules.py`:

```python
def mass_starrer(target: str, events: Sequence[Event], t: Thresholds) -> Label | None:
    stars = [e for e in events if e.type == "WatchEvent"]
    window = densest_window(stars, _when, t.window)
    return _window_label("mass-starrer", target, window, t.mass_stars_by_actor)
```

1. **Threshold**: add a field to `Thresholds` (`mass_stars_by_actor: int = 100`).
2. **Rule**: write the function. Helpers: `densest_window()` (the busiest window, optionally
   weighted), `gap_variation()` (how evenly spaced events are), `_window_label()` (builds the
   label with confidence and evidence).
3. **Register** it in `ACTOR_RULES`, `REPO_RULES` or `GIST_OWNER_RULES`.
4. **Test** it in `tests/test_pipeline.py` with `make_event(...)`: one case that fires, one
   that stays quiet.
5. **Document** it: the labels table in the root `README.md` and the [[label]] page.

Confidence is 0.5 exactly at the threshold and grows to 1.0 at twice the threshold.
