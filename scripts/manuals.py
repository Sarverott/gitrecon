"""Read the documentation in docs/ from the terminal: ``task manuals [-- PAGE]``.

The implementation lives in ``gitrecon.tui.manuals`` (the interactive menu uses it too).
"""

import sys

from gitrecon.tui.manuals import main

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
