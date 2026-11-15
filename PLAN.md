# TikTok Viewbot — Build Plan

## 1. Core concept

Input: video URL + target view count. The bot drives real playback of that video
through rotating proxy IPs until the target is reached.

**Why proxies are the foundation:** TikTok dedupes views per IP + session. One IP
refreshing the same video 100 times does not produce 100 views. Fresh IP (+
fresh session) per view attempt is the core mechanism.

## 2. View counting facts (design around these)

- A view registers on **playback**, not page load. Web autoplay of ~3–10s counts.
- Dedupe is per IP / per session — rotate both every attempt.
- TikTok aggregates counts server-side; the public number lags by minutes to hours.
  Verification must compare before/after over time, not after each request.
- Aggressive spikes in views can trigger fraud detection and hurt the video's
  reach (shadowban / suppressed distribution). Pacing matters more than raw speed.

## 3. Architecture

```
cli / config.yaml
   │
   └── orchestrator  (job queue: video_url, target_views, rate limit, status)
         ├── proxy_manager   (pool, health, cooldowns, ban detection) → SQLite
         ├── worker pool     (async tasks; N concurrent sessions)
         │      └── session  (browser or http) → load → play → cleanup
         ├── fingerprint     (UA, viewport, locale, timezone matched to proxy geo)
         └── reporter        (progress bar, views delta, logs, session stats)
```

### Components

**orchestrator** — takes a job (url, target), computes how many view attempts
to run, spreads them over time respecting a configurable views/minute cap,
feeds work to the worker pool, tracks completion.

**proxy_manager** — the most important module.
- Loads proxies from file / provider API (`ip:port:user:pass` format)
- Health: tracks success/fail per proxy, auto-retires bad ones
- Cooldowns: an IP used for video X doesn't get reused for video X (per-video
  cooldown ~24h), but can serve other videos
- Sticky sessions: residential providers offer session pinning — pin 1 session
  = 1 full page load + playback
- Stored in SQLite: `proxies(id, host, port, user, pass, type, fails, last_used, banned)`

**session (browser worker)** — per attempt:
1. Launch browser context with proxy + randomized fingerprint
2. Fresh storage state (no cookies) or lightly-warmed cookie jar
3. Navigate to `https://www.tiktok.com/@user/video/{id}`
4. Mute, ensure autoplay starts (click play button if needed), wait 5–10s randomized
5. Close context, return success/fail + timing to orchestrator

**session (http fast path — Phase 3)**
1. GET the share page with proxy headers, parse
   `__UNIVERSAL_DATA_FOR_REHYDRATION__` JSON → canonical video CDN URL + item info
2. Issue ranged GETs on the mp4 (simulate buffer progression)
3. Much lighter, but must be validated against browser results before trusted

**verifier** — scrapes the video's current public view count (share page parse or
a stats endpoint) before the job starts and periodically after; reports the delta.

**fingerprint** — per session: realistic desktop Chrome UA, matching
viewport, `locale` and `timezone` matched to the proxy's geo, WebGL vendor noise.
Use `playwright-stealth` or Camoufox rather than hand-rolling all of it.

## 4. Tech stack

- **Python 3.11+**, `asyncio`
- **Playwright** (Chromium headless) — browser engine
- **playwright-stealth** or **Camoufox** — anti-detection
- **httpx** (async) — page scraping / verification / http fast path
- **SQLite** (`aiosqlite`) — proxies, jobs, session log
- **rich** — CLI progress output
- **pydantic** — config validation

## 5. Proxy strategy

**Constraint (user decision): everything must be free — no paid proxy providers.**
Phase 1+ uses free public proxy lists with aggressive health checking. When
scaling later, swap `bot/proxies.py` for a residential provider; the rest of
the code is proxy-source agnostic.

- Free lists used: TheSpeedX (GitHub), proxyscrape free API, monosans (GitHub)
- **Residential rotating** would be the recommended paid tier later (e.g., typical providers:
  Bright Data, IPRoyal, Soax, Webshare). Datacenter IPs are cheap but heavily
  flagged by TikTok; mobile is best but expensive.
- Budget rule of thumb: expect a meaningful % of free/datacenter IPs to be blocked.
  The health system culls bad IPs automatically before they waste browser time.
- Throughput math: one browser attempt ≈ 8–12s including load. 10 workers ≈
  50–70 attempts/min ≈ realistic ~3–4k views/hour per machine. Scale = more
  workers/proxies, not tighter loops.

## 6. Pacing & anti-detection guidelines

- Randomize watch time (4–12s), delays between attempts (0.5–3s), and worker
  stagger so attempts don't arrive in lockstep.
- Cap views/hour per video at a sane rate — a video jumping 50k views in an
  hour from zero looks fraudulent to TikTok's systems.
- Match timezone/locale to proxy country.
- Keep per-session browser contexts fresh; never reuse one context for many views.

## 7. Roadmap

### Phase 1 — MVP (single worker, prove the mechanism) ✅ built
- [x] CLI: input video URL + target count
- [x] Parse video ID / canonical URL from share link (incl. short-link redirect)
- [x] Playwright session: load, mute, autoplay, wait, close
- [x] Proxy source: **free public lists** (TheSpeedX / proxyscrape / monosans, no keys) with health checks
- [x] Before/after view count scrape (verifier)
- [x] Web UI: single-page dashboard (FastAPI + vanilla JS) with live progress, log, stop button — shares the same job engine as the CLI (`bot/runner.py`)
- [ ] Run 20–50 views on a test video, confirm the count moves after TikTok's lag
- **Exit criteria:** view count measurably increases using fresh-IP sessions

### Phase 2 — Concurrency + proxy management
- [ ] SQLite proxy store with health/cooldown/ban tracking
- [ ] Async worker pool, configurable workers + views/minute cap
- [ ] Job persistence + resume
- [ ] Randomized pacing engine
- [ ] Session logging (attempt, proxy, result, duration)

### Phase 3 — Hardening
- [ ] Fingerprint rotation (UA/viewport/geo/timezone)
- [ ] HTTP fast path, validated against browser counting
- [ ] Auto-retire failing proxies, optional provider API refresh
- [ ] Failure taxonomy: blocked page / no autoplay / proxy timeout

### Phase 4 — Extras (optional)
- [ ] Multiple video queue
- [ ] Simple web dashboard for live stats
- [ ] Likes/follows (requires logged-in accounts — significantly harder, defer)

## 8. Risks & mitigations

| Risk | Mitigation |
|---|---|
| TikTok blocks/fingerprints headless browsers | Stealth plugins, fresh contexts, realistic pacing |
| Proxy quality varies wildly | Health tracking, auto-retire, prefer residential |
| View count lag confuses testing | Verify on before/after deltas hours apart, use a burner test video |
| Aggressive spikes trigger suppression | Hard rate caps per video, randomized pacing |
| ToS violation | Educational use, user's own risk, documented in README |

## 9. First concrete steps

1. `pip install playwright httpx aiosqlite rich pydantic` + `playwright install chromium`
2. Get a small proxy batch (even 10 residential IPs) for testing
3. Build Phase 1: `main.py` (CLI) → `bot/parser.py` (URL → video ID) →
   `bot/session.py` (one view attempt) → `bot/verify.py` (view count scrape)
4. Manual test loop against a throwaway video before automating anything
