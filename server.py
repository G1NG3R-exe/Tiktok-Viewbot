"""TikTok Viewbot — local web UI server.

Serves the single-page frontend from web/ and a small JSON API.
Run:  python server.py   then open http://127.0.0.1:8788
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from bot.runner import BoostJob, run_boost

WEB_DIR = Path(__file__).parent / "web"
PORT = 8788

app = FastAPI(title="TikTok Viewbot")
job = BoostJob()
task: asyncio.Task | None = None


class StartRequest(BaseModel):
    url: str
    views: int = 20
    use_proxies: bool = True
    workers: int = 8


@app.post("/api/start")
async def start_job(req: StartRequest) -> dict:
    global task
    if job.is_busy:
        raise HTTPException(status_code=409, detail="A job is already running")
    url = req.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="Video URL is required")
    if req.views < 1:
        raise HTTPException(status_code=400, detail="View count must be at least 1")
    if req.views > 100_000:
        raise HTTPException(status_code=400, detail="Keep targets under 100,000 views")
    workers = max(1, min(req.workers, 24))

    job.reset()
    task = asyncio.create_task(run_boost(job, url, req.views, req.use_proxies, workers=workers))
    return {"ok": True}


@app.get("/api/status")
async def status() -> dict:
    return job.snapshot()


@app.post("/api/stop")
async def stop_job() -> dict:
    if job.is_busy:
        job.stop_requested = True
        return {"ok": True, "detail": "Stopping after the current attempt"}
    return {"ok": False, "detail": "Nothing is running"}


# Static frontend last, so /api/* routes take priority
app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")


if __name__ == "__main__":
    print(f"TikTok Viewbot UI  ->  http://127.0.0.1:{PORT}")
    try:
        uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")
    except OSError as exc:
        if "10048" in str(exc) or "only one usage" in str(exc).lower():
            print(
                f"Port {PORT} is already in use — the UI is probably already "
                f"running at http://127.0.0.1:{PORT}"
            )
        else:
            raise

