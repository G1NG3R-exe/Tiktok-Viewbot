"""Browser playback session: one proxied 'real' view attempt.

Uses Playwright Chromium. The browser is launched with a placeholder global
proxy so that each context can override it with its own proxy (a Playwright
Chromium feature). Each attempt gets a fresh context = fresh session.
"""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass

from playwright.async_api import async_playwright

USER_AGENTS = [
    # Desktop Chrome on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    # Desktop Chrome on macOS
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    # Desktop Edge on Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0",
]

VIEWPORTS = [(1280, 720), (1366, 768), (1440, 900), (1536, 864), (1920, 1080)]

LOCALES = ["en-US", "en-GB", "en-CA", "en-AU"]


def random_user_agent() -> str:
    return random.choice(USER_AGENTS)


@dataclass
class AttemptResult:
    loaded: bool          # page loaded at all
    played: bool          # video actually started playing
    seconds: float        # wall time of the attempt
    proxy: str | None


async def watch_once(
    page_factory,
    video_url: str,
    proxy: str | None = None,
    watch_range: tuple[float, float] = (5.0, 10.0),
) -> AttemptResult:
    """Run one view attempt inside a fresh browser context.

    `page_factory` is an async callable returning a new Page bound to a
    context configured with the given proxy. Returns an AttemptResult.
    """
    started = time.monotonic()
    width, height = random.choice(VIEWPORTS)

    try:
        page = await page_factory(
            proxy=proxy,
            user_agent=random_user_agent(),
            viewport={"width": width, "height": height},
            locale=random.choice(LOCALES),
        )
        await page.goto(video_url, timeout=45_000, wait_until="domcontentloaded")

        # Make sure the video element exists and starts playing, muted.
        try:
            await page.evaluate(
                """() => {
                    const v = document.querySelector('video');
                    if (v) { v.muted = true; v.play().catch(() => {}); }
                }"""
            )
        except Exception:
            pass

        await asyncio.sleep(random.uniform(*watch_range))

        played = await page.evaluate(
            "() => { const v = document.querySelector('video');"
            " return !!v && v.currentTime > 0; }"
        )
        await page.context.close()
        return AttemptResult(True, bool(played), time.monotonic() - started, proxy)
    except Exception:
        return AttemptResult(False, False, time.monotonic() - started, proxy)


async def launch_browser():
    """Launch Chromium with the placeholder global proxy required for
    per-context proxy overrides. Returns the playwright/browser pair —
    caller must close both."""
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(
        headless=True,
        proxy={"server": "http://per-context"},  # placeholder, overridden per context
        args=["--disable-blink-features=AutomationControlled"],
        ignore_default_args=["--enable-automation"],
    )
    return playwright, browser


async def make_page_factory(browser):
    """Return an async factory that creates a fresh context+page with the
    given proxy/fingerprint settings."""

    async def factory(proxy: str | None, user_agent: str, viewport: dict, locale: str):
        # Only pass proxy when set — passing proxy=None would make the context
        # inherit the placeholder global proxy instead of going direct.
        context_kwargs: dict = {
            "user_agent": user_agent,
            "viewport": viewport,
            "locale": locale,
        }
        if proxy:
            context_kwargs["proxy"] = {"server": f"http://{proxy}"}
        context = await browser.new_context(**context_kwargs)
        return await context.new_page()

    return factory
