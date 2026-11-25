"""Command line: ``python -m isodraw demo [out.svg]`` writes the demo / self-test sheet."""

import sys
from typing import List, Optional

from . import __version__, demo

USAGE = "usage: python -m isodraw demo [out.svg]  |  python -m isodraw --version"


def main(argv: Optional[List[str]] = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] in ("--version", "-V"):
        print(__version__)
        return 0
    if not args or args[0] != "demo" or len(args) > 2:
        print(USAGE, file=sys.stderr)
        return 2
    print(demo(args[1] if len(args) == 2 else "isodraw_demo.svg"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
