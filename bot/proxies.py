"""Free proxy sourcing and health checking.

No paid providers and no API keys — proxies come from public free lists
(GitHub-maintained + free API endpoints). Free proxies are unreliable, so
every proxy is health-checked against tiktok.com before it is used, and
the caller should expect a meaningful share of attempts to fail.
"""

from __future__ import annotations

import asyncio
import random

import httpx

# Public free proxy lists (plain "ip:port" or "scheme://ip:port" lines)
SOURCES = [
    "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
    "https://api.proxyscrape.com/v2/?request=displayproxies&protocol=http&timeout=10000",
    "https://raw.githubusercontent.com/monosans/proxy-list/main/proxies/http.txt",
]

# How many candidates to pull / health-check per run
MAX_CANDIDATES = 300
MAX_WORKING = 50
CHECK_CONCURRENCY = 50
CHECK_TIMEOUT = 10
PROBE_URL = "https://www.tiktok.com/oembed?url=https://www.tiktok.com/@x/video/7704552985422073119"


def _normalize(line: str) -> str | None:
    line = line.strip()
    if not line:
        return None
    # monosans list lines look like "http://1.2.3.4:8080"
    for prefix in ("http://", "https://"):
        if line.startswith(prefix):
            line = line[len(prefix):]
            break
    host, _, port = line.partition(":")
    if not host or not port.isdigit():
        return None
    return f"{host}:{port}"


async def fetch_candidates() -> list[str]:
    """Pull raw proxy lists from all sources, deduplicated and shuffled."""
    proxies: set[str] = set()

    async def grab(client: httpx.AsyncClient, source: str) -> None:
        try:
            response = await client.get(source, timeout=20)
            for line in response.text.splitlines():
                proxy = _normalize(line)
                if proxy:
                    proxies.add(proxy)
        except httpx.HTTPError:
            pass  # a dead source shouldn't kill the run

    async with httpx.AsyncClient() as client:
        await asyncio.gather(*(grab(client, source) for source in SOURCES))

    candidates = list(proxies)
    random.shuffle(candidates)
    return candidates[:MAX_CANDIDATES]


async def _check(proxy: str, semaphore: asyncio.Semaphore, probe_url: str) -> str | None:
    """A proxy 'works' if it can fetch TikTok over HTTPS.

    The homepage alone is too weak a signal — most proxies that pass it still
    choke on a video page — so the probe is a small oembed request instead.
    """
    async with semaphore:
        try:
            async with httpx.AsyncClient(
                proxy=f"http://{proxy}", timeout=CHECK_TIMEOUT, follow_redirects=True
            ) as client:
                response = await client.get(probe_url)
            if response.status_code == 200 and '"type":"video"' in response.text:
                return proxy
        except httpx.HTTPError:
            pass
    return None


async def get_working_proxies(limit: int = MAX_WORKING, probe_url: str = PROBE_URL) -> list[str]:
    """Fetch candidates and return up to `limit` verified-working proxies."""
    candidates = await fetch_candidates()
    if not candidates:
        return []

    semaphore = asyncio.Semaphore(CHECK_CONCURRENCY)
    results = await asyncio.gather(
        *(_check(proxy, semaphore, probe_url) for proxy in candidates)
    )

    working = [proxy for proxy in results if proxy]
    random.shuffle(working)
    return working[:limit]
