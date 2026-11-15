"""TikTok Viewbot — CLI frontend.

Give it a video URL and a target view count; it drives real playback of the
video through rotating free proxies until the target is reached.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from rich.console import Console

from bot.runner import BoostJob, run_boost
from bot.verify import get_view_count
from bot.parser import canonical_url, extract_video_id, resolve_url

console = Console()

LEVEL_STYLES = {"success": "cyan", "error": "red", "info": "default"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="TikTok view booster (CLI)")
    parser.add_argument("url", nargs="?", help="TikTok video URL")
    parser.add_argument("-n", "--views", type=int, default=20, help="Target view count")
    parser.add_argument(
        "--no-proxy", action="store_true", help="Use your own IP (small counts only)"
    )
    parser.add_argument(
        "--max-attempts-multiplier",
        type=int,
        default=4,
        help="Give up after this many attempts per requested view",
    )
    return parser.parse_args()


async def run_cli(url: str, target: int, use_proxies: bool, multiplier: int) -> int:
    console.rule("[bold]TikTok Viewbot")

    job = BoostJob()
    printed = 0

    def on_update(snapshot: dict) -> None:
        nonlocal printed
        for entry in snapshot["log"][printed:]:
            style = LEVEL_STYLES.get(entry["level"], "default")
            mark = {"success": "[cyan]+[/cyan]", "error": "[red]x[/red]"}.get(
                entry["level"], "|"
            )
            console.print(f"{mark} {entry['text']}", style=style)
            printed += 1

    job.on_update = on_update
    await run_boost(job, url, target, use_proxies, multiplier)

    if job.status == "done":
        console.print(f"\n[bold]{job.successes}/{job.target}[/bold] views delivered.")
    elif job.error:
        console.print(f"\n[red]{job.error}[/red]")
        return 1
    console.print(
        "[dim]TikTok aggregates counts server-side - re-check the view count "
        "in 10-60 minutes to see the delta.[/dim]"
    )
    return 0


def main() -> None:
    args = parse_args()
    url = args.url
    if not url:
        url = console.input("[bold]Enter TikTok video URL:[/bold] ").strip()
    if not args.views or args.views < 1:
        console.print("[red]View count must be at least 1.[/red]")
        sys.exit(1)
    sys.exit(asyncio.run(run_cli(url, args.views, not args.no_proxy, args.max_attempts_multiplier)))


if __name__ == "__main__":
    main()
