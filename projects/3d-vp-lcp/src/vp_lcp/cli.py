"""Minimal CLI entry point."""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="vp-lcp",
        description="3D Vertical Permeability Least-Cost Path framework.",
    )
    parser.add_argument("--version", action="store_true", help="Print version and exit.")
    args = parser.parse_args(argv)

    if args.version:
        from . import __version__

        print(f"vp-lcp {__version__}")
        sys.exit(0)

    parser.print_help()


if __name__ == "__main__":
    main()
