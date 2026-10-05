# Translation

> Offline translation with Argos Translate, the engine inside LibreTranslate.

## What it is

Language packages are installed once (about 100 MB each, one direction each: `en` -> `pl`);
after that translation runs on this machine with no network. Between two languages without
a direct package Argos goes through English when both halves are installed.

## Where

`gitrecon.translate` (`installed_languages`, `available_packages`, `install`, `translate`);
needs the `translate` extra. CLI: `gitrecon translate languages [--available]`,
`gitrecon translate install FROM TO`, `gitrecon translate text --from CODE --to CODE WORDS...`.

> **Remember!** Packages are kept by Argos, not in gitrecon's data folder:
> `~/.local/share/argos-translate` (`ARGOS_PACKAGES_DIR` moves them).

## Relations

The same packages a LibreTranslate server would use.
