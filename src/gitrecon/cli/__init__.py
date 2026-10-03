"""gitrecon command line: collect -> buffer -> map -> label.

Commands live in modules by what they do (``collect``, ``analyze``, ``atlas``,
``content``); each registers its subparsers. How anything is printed - text,
``--json``, ``--urls`` - is decided in ``output``.
"""

from __future__ import annotations

import argparse
import logging

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
    return parser


def main(argv: list[str] | None = None) -> int:
    load_env()
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return args.func(args, Config(), Output.of(args))
