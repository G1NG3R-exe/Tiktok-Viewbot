"""URL parsing helpers for TikTok video links."""

from __future__ import annotations

import re

import httpx

VIDEO_ID_RE = re.compile(r"/(?:video|v)/(\d+)")


def extract_video_id(url: str) -> str:
    """Extract the numeric video ID from a TikTok URL."""
    match = VIDEO_ID_RE.search(url)
    if not match:
        raise ValueError(
            f"Could not find a video ID in '{url}'. "
            "Expected something like https://www.tiktok.com/@user/video/1234567890"
        )
    return match.group(1)


def canonical_url(video_id: str) -> str:
    """Build a canonical web URL for a video ID.

    The username segment is cosmetic; `@x` avoids needing the author and keeps
    us off `/tiktokstudio/`, whose page embeds a different (wrong) play count.
    """
    return f"https://www.tiktok.com/@x/video/{video_id}"


def player_url(video_id: str) -> str:
    """Lightweight official embed player — far easier to load through a proxy
    than the full video page."""
    return (
        f"https://www.tiktok.com/player/v1/{video_id}"
        "?autoplay=1&muted=1&music_info=1&description=1"
    )


async def resolve_url(url: str) -> str:
    """Follow short-link redirects (vm.tiktok.com, vt.tiktok.com) and return
    a full URL containing the video ID."""
    if "/video/" in url:
        return url
    async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
        response = await client.get(url)
    return str(response.url)
