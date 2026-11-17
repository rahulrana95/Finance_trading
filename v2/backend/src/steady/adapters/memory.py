"""In-memory store for runs and ideas, until the database exists. Lost on restart."""

import threading
from collections import deque
from dataclasses import replace

from steady.constants import IDEA_EXPIRED, IDEA_NEW, MAX_RUNS_KEPT
from steady.domain import Idea, Run


class MemoryStore:
    def __init__(self, max_runs: int = MAX_RUNS_KEPT) -> None:
        self.lock = threading.Lock()
        self._runs: deque[Run] = deque(maxlen=max_runs)
        self._ideas: dict[str, Idea] = {}

    def add_run(self, run: Run) -> None:
        self._runs.appendleft(run)

    def runs(self) -> list[Run]:
        return list(self._runs)

    def run(self, run_id: str) -> Run | None:
        return next((r for r in self._runs if r.id == run_id), None)

    def save_idea(self, idea: Idea) -> None:
        self._ideas[idea.id] = idea

    def ideas(self) -> list[Idea]:
        return sorted(self._ideas.values(), key=lambda i: i.created_at, reverse=True)

    def open_idea(self, symbol: str) -> Idea | None:
        return next(
            (i for i in self._ideas.values() if i.symbol == symbol and i.status == IDEA_NEW), None
        )

    def expire(self, idea: Idea) -> None:
        self._ideas[idea.id] = replace(idea, status=IDEA_EXPIRED)
