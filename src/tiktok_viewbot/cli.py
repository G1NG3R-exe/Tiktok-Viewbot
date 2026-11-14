"""Command-line interface for the viewbot.

Argument parsing only for now — wiring up the worker is part of the roadmap.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from tiktok_viewbot import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="viewbot",
        description="Send views to a TikTok video.",
    )
    parser.add_argument("url", help="public TikTok video URL")
    parser.add_argument(
        "-n",
        "--views",
        type=int,
        default=100,
        metavar="COUNT",
        help="number of views to send (default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate the URL and show the plan without sending views",
    )
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    print(f"TikTok Viewbot v{__version__}")
    print(f"  url:   {args.url}")
    print(f"  views: {args.views}")
    print("Not implemented yet.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
