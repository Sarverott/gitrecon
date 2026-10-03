"""Entry point of the ``gitrecon`` command (the commands live in ``gitrecon.cli``)."""

import sys

from gitrecon.cli import build_parser, main

__all__ = ["build_parser", "main"]

if __name__ == "__main__":
    sys.exit(main())
