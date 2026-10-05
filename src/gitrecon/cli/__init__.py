"""gitrecon command line: collect -> buffer -> map -> label.

Commands live in modules by what they do (``collect``, ``analyze``, ``atlas``,
``content``); each registers its subparsers. How anything is printed - text,
``--json``, ``--urls`` - is decided in ``output``.
"""

from __future__ import annotations

import argparse
import logging
import sys

from gitrecon.cli import analyze, atlas, collect, content
from gitrecon.cli.output import Output
from gitrecon.config import Config, load_env

MODULES = (collect, analyze, atlas, content)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gitrecon",
        description=__doc__.split("\n", 1)[0],
        epilog="Most commands take --json (data for programs) and --urls (web addresses, one per line).",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)
    for module in MODULES:
        module.register(sub)
    menu = sub.add_parser("menu", help="interactive menu: commands, tasks, examples, manuals, status")
    menu.set_defaults(func=_menu)
    return parser


def _menu(args: argparse.Namespace, config: Config, out: Output) -> int:
    from gitrecon.tui.app import run_menu

    return run_menu(config)


def _late_positionals(parser: argparse.ArgumentParser, args: argparse.Namespace, rest: list[str]) -> None:
    """Give words that follow the options to the command's list argument (``rest=`` in its defaults).

    ``gitrecon translate text --from en --to pl hello world``: Python before 3.12.7 closes a
    ``nargs="*"`` positional as soon as an option follows the subcommand and then rejects
    ``hello world``; newer versions accept it. Collecting them here makes both behave alike.
    """
    dest = getattr(args, "rest", None)
    if dest is None or any(word.startswith("-") and word != "-" for word in rest):
        parser.error(f"unrecognized arguments: {' '.join(rest)}")
    given = getattr(args, dest)
    setattr(args, dest, rest if given in ([], None) or getattr(args, "rest_default", None) == given else [*given, *rest])


def main(argv: list[str] | None = None) -> int:
    load_env()
    if argv is None and len(sys.argv) == 1 and sys.stdin.isatty() and sys.stdout.isatty():
        argv = ["menu"]  # plain `gitrecon` in a terminal opens the menu
    parser = build_parser()
    args, rest = parser.parse_known_args(argv)
    if rest:
        _late_positionals(parser, args, rest)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return args.func(args, Config(), Output.of(args))
