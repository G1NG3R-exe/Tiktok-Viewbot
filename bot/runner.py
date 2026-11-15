"""Job runner: drives a full boost run and exposes its state.

Both frontends (CLI and web) consume the same BoostJob state object, so the
engine has exactly one source of truth.
"""

from __future__ import annotations

import asyncio
import random
import time
from collections.abc import Callable
from dataclasses import dataclass, field

from .parser import canonical_url, extract_video_id, player_url, resolve_url
from .proxies import get_working_proxies
from .session import launch_browser, make_page_factory, watch_once
from .verify import get_view_count

IDLE = "idle"
QUEUED = "queued"
RESOLVING = "resolving"
PROXIES = "proxies"
RUNNING = "running"
DONE = "done"
ERROR = "error"
STOPPED = "stopped"

TERMINAL_STATUSES = {DONE, ERROR, STOPPED}

MAX_LOG_LINES = 500


@dataclass
class BoostJob:
    status: str = IDLE
    url: str = ""
    video_id: str = ""
    target: int = 0
    baseline: int | None = None
    attempts: int = 0
    successes: int = 0
    proxies_found: int = 0
    use_proxies: bool = True
    workers: int = 8
    error: str | None = None
    started_at: float | None = None
    finished_at: float | None = None
    stop_requested: bool = False
    log: list[dict] = field(default_factory=list)
    on_update: Callable[[BoostJob], None] | None = field(default=None, repr=False)

    def reset(self) -> None:
        self.status = IDLE
        self.url = ""
        self.video_id = ""
        self.target = 0
        self.baseline = None
        self.attempts = 0
        self.successes = 0
        self.proxies_found = 0
        self.use_proxies = True
        self.workers = 8
        self.error = None
        self.started_at = None
        self.finished_at = None
        self.stop_requested = False
        self.log = []
        self._changed()

    @property
    def is_busy(self) -> bool:
        return self.status not in (IDLE, *TERMINAL_STATUSES)

    def set(self, **kwargs) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)
        self._changed()

    def add_log(self, text: str, level: str = "info") -> None:
        self.log.append({"t": time.time(), "text": text, "level": level})
        if len(self.log) > MAX_LOG_LINES:
            del self.log[: len(self.log) - MAX_LOG_LINES]
        self._changed()

    def snapshot(self) -> dict:
        return {
            "status": self.status,
            "url": self.url,
            "video_id": self.video_id,
            "target": self.target,
            "baseline": self.baseline,
            "attempts": self.attempts,
            "successes": self.successes,
            "proxies_found": self.proxies_found,
            "use_proxies": self.use_proxies,
            "workers": self.workers,
            "error": self.error,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "log": self.log[-200:],
        }

    def _changed(self) -> None:
        if self.on_update is not None:
            try:
                self.on_update(self.snapshot())
            except Exception:
                pass


class _ProxyRotator:
    """Hands out proxies round-robin, reshuffling once the list is spent.

    Consecutive workers get different proxies, so a wave of attempts doesn't
    pile onto one IP (TikTok dedupes views per IP). A proxy that fails twice
    is retired; when none are left the caller gets None (direct connection).
    """

    RETIRE_AFTER = 2

    def __init__(self, proxies: list[str]) -> None:
        self._items = proxies
        self._order: list[str] = []
        self._index = 0
        self._failures: dict[str, int] = {}
        self._lock = asyncio.Lock()

    def fail(self, proxy: str | None) -> None:
        if not proxy:
            return
        failures = self._failures.get(proxy, 0) + 1
        self._failures[proxy] = failures
        if failures >= self.RETIRE_AFTER and proxy in self._order:
            self._order.remove(proxy)
            self._index = min(self._index, len(self._order))

    async def next(self) -> str | None:
        async with self._lock:
            if not self._order:
                self._order = [
                    p for p in self._items if self._failures.get(p, 0) < self.RETIRE_AFTER
                ]
                if not self._order:
                    return None
                random.shuffle(self._order)
                self._index = 0
            if self._index >= len(self._order):
                random.shuffle(self._order)
                self._index = 0
            proxy = self._order[self._index]
            self._index += 1
            return proxy


async def run_boost(
    job: BoostJob,
    url: str,
    target: int,
    use_proxies: bool = True,
    multiplier: int = 4,
    workers: int = 8,
) -> None:
    """Run a complete boost job, keeping `job` updated throughout."""

    def check_stop() -> bool:
        return job.stop_requested

    job.set(
        target=target,
        use_proxies=use_proxies,
        started_at=time.time(),
        status=RESOLVING,
    )
    job.add_log(f"Resolving {url}")

    playwright = browser = None
    try:
        # 1. Resolve URL / extract video ID
        try:
            resolved = await resolve_url(url)
            video_id = extract_video_id(resolved)
        except ValueError as exc:
            job.add_log(str(exc), level="error")
            job.set(status=ERROR, error=str(exc))
            return
        if check_stop():
            job.set(status=STOPPED)
            return

        job.set(video_id=video_id)
        page_url = canonical_url(video_id)
        watch_url = player_url(video_id)
        job.add_log(f"Video ID {video_id}", level="success")

        # 2. Baseline view count
        job.set(status=RESOLVING)
        job.add_log("Reading current view count...")
        baseline = await get_view_count(page_url)
        if baseline is not None:
            job.set(baseline=baseline)
            job.add_log(f"Baseline: {baseline:,} views (public count lags reality)")
        else:
            job.add_log("Could not read baseline count - continuing anyway", level="error")

        # 3. Proxies
        proxies: list[str] = []
        if use_proxies:
            job.set(status=PROXIES)
            job.add_log("Fetching and testing free proxies (can take a minute)...")
            proxies = await get_working_proxies(
                probe_url=f"https://www.tiktok.com/oembed?url={page_url}"
            )
            job.set(proxies_found=len(proxies))
            if proxies:
                job.add_log(f"{len(proxies)} working proxies ready", level="success")
            else:
                job.add_log(
                    "No working free proxies found - using your own IP "
                    "(expect heavy view dedup)",
                    level="error",
                )
        if check_stop():
            job.set(status=STOPPED)
            return

        # 4. Playback attempts — run a pool of workers so views land in parallel
        if proxies:
            # More sessions than proxies just means hammering the same IPs
            effective_workers = max(1, min(workers, len(proxies)))
            if effective_workers < workers:
                job.add_log(
                    f"Only {len(proxies)} proxies — running {effective_workers} parallel sessions",
                    level="error",
                )
        else:
            effective_workers = workers
        job.set(status=RUNNING, workers=effective_workers)
        max_attempts = max(target * multiplier, 20)
        rotator = _ProxyRotator(proxies)
        in_flight = 0
        fell_back = False

        playwright, browser = await launch_browser()
        factory = await make_page_factory(browser)

        async def worker(slot: int) -> None:
            nonlocal in_flight, fell_back
            # Stagger startup so context/browser creation doesn't burst
            await asyncio.sleep(slot * 0.3)
            while job.successes + in_flight < target and job.attempts < max_attempts:
                if check_stop():
                    return
                job.attempts += 1
                in_flight += 1
                job.set(attempts=job.attempts)
                proxy = await rotator.next()
                if proxy is None and proxies and not fell_back:
                    fell_back = True
                    job.add_log(
                        "All proxies failed twice - falling back to your own IP",
                        level="error",
                    )
                try:
                    result = await watch_once(factory, watch_url, proxy=proxy)
                finally:
                    in_flight -= 1
                label = proxy or "direct"
                if result.played:
                    job.successes += 1
                    job.add_log(
                        f"View {job.successes}/{target} via {label} ({result.seconds:.1f}s)",
                        level="success",
                    )
                else:
                    rotator.fail(proxy)
                    job.add_log(f"Attempt failed via {label} - retrying", level="error")
                await asyncio.sleep(random.uniform(0.2, 0.8))

        await asyncio.gather(*(worker(slot) for slot in range(effective_workers)))

        if check_stop():
            job.set(status=STOPPED)
        elif job.successes >= target:
            job.add_log(f"Target reached: {job.successes}/{target} views", level="success")
            job.set(status=DONE)
        else:
            job.set(status=ERROR, error=f"Ran out of attempts ({job.attempts}) with "
                                        f"{job.successes}/{target} views")
            job.add_log(job.error, level="error")
    except asyncio.CancelledError:
        job.set(status=STOPPED)
        job.add_log("Job cancelled", level="error")
        raise
    except Exception as exc:  # keep the job alive on unexpected errors
        job.set(status=ERROR, error=str(exc))
        job.add_log(f"Unexpected error: {exc}", level="error")
    finally:
        job.set(finished_at=time.time())
        if browser is not None:
            try:
                await browser.close()
            except Exception:
                pass
        if playwright is not None:
            try:
                await playwright.stop()
            except Exception:
                pass
