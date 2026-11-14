"""The worker that will actually deliver views.

Everything here is a skeleton; see the roadmap in the README.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ViewJob:
    """A single request to add ``views`` views to ``url``."""

    url: str
    views: int


class ViewBot:
    """Coordinates resolving a video and sending views to it."""

    def __init__(self, job: ViewJob, workers: int = 4) -> None:
        self.job = job
        self.workers = workers

    def run(self) -> int:
        """Send the requested views and return how many were delivered."""
        raise NotImplementedError("view delivery is not implemented yet")
