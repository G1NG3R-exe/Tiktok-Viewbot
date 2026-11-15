"""View-count verification.

Primary source: scrape the video page and read the playCount embedded in the
__UNIVERSAL_DATA_FOR_REHYDRATION__ JSON blob.
Fallback: tikwm.com public API (free, no key).

Note: TikTok aggregates view counts server-side, so the public number lags
real playback by minutes to hours. Always compare before/after deltas.
"""

from __future__ import annotations

import json
import re

import httpx

from .session import random_user_agent

UNIVERSAL_DATA_RE = re.compile(
    r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', re.S
)
PLAYCOUNT_RE = re.compile(r'"playCount":\s*"?(\d+)"?')


def _proxy_url(proxy: str | None) -> str | None:
    """Accept both "ip:port" and full URLs; httpx needs a scheme."""
    if proxy and "://" not in proxy:
        return f"http://{proxy}"
    return proxy


async def _count_from_page(video_url: str, proxy: str | None) -> int | None:
    headers = {"User-Agent": random_user_agent()}
    async with httpx.AsyncClient(
        proxy=_proxy_url(proxy), headers=headers, timeout=20, follow_redirects=True
    ) as client:
        response = await client.get(video_url)
    html = response.text

    match = UNIVERSAL_DATA_RE.search(html)
    if match:
        try:
            data = json.loads(match.group(1))
            item = data["__DEFAULT_SCOPE__"]["webapp.video-detail"]["itemInfo"][
                "itemStruct"
            ]
            return int(item["stats"]["playCount"])
        except (KeyError, TypeError, ValueError):
            pass

    fallback = PLAYCOUNT_RE.search(html)
    if fallback:
        return int(fallback.group(1))
    return None


async def _count_from_tikwm(video_url: str) -> int | None:
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                "https://www.tikwm.com/api/", params={"url": video_url}
            )
        data = response.json().get("data") or {}
        count = int(data.get("play_count", 0))
        return count or None
    except (httpx.HTTPError, ValueError):
        return None


async def get_view_count(video_url: str, proxy: str | None = None) -> int | None:
    """Return the current public play count, or None if it can't be read."""
    count = await _count_from_page(video_url, proxy)
    if count is not None:
        return count
    return await _count_from_tikwm(video_url)
