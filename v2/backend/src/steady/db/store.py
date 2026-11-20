"""Runs and ideas kept in the database. Same shape as the in-memory store."""

import threading

from sqlalchemy import Engine, select, update
from sqlalchemy.orm import Session

from steady.constants import IDEA_EXPIRED, IDEA_NEW, MAX_RUNS_KEPT
from steady.db.codec import idea_values, run_values, screen_values, to_idea, to_run, to_screen
from steady.db.models import IdeaRow, RunRow, ScreenRecord
from steady.domain import Idea, Run, Screen


class SqlStore:
    def __init__(self, engine: Engine, max_runs: int = MAX_RUNS_KEPT) -> None:
        self.lock = threading.Lock()
        self._engine = engine
        self._max_runs = max_runs

    def add_run(self, run: Run) -> None:
        with Session(self._engine) as session, session.begin():
            session.add(RunRow(id=run.id, **run_values(run)))

    def save_run(self, run: Run) -> None:
        with Session(self._engine) as session, session.begin():
            session.execute(update(RunRow).where(RunRow.id == run.id).values(**run_values(run)))

    def runs(self) -> list[Run]:
        """The latest runs, newest first. Older ones stay in the table."""
        query = select(RunRow).order_by(RunRow.seq.desc()).limit(self._max_runs)
        with Session(self._engine) as session:
            return [to_run(row) for row in session.scalars(query)]

    def run(self, run_id: str) -> Run | None:
        with Session(self._engine) as session:
            row = session.scalars(select(RunRow).where(RunRow.id == run_id)).first()
            return to_run(row) if row else None

    def save_idea(self, idea: Idea) -> None:
        with Session(self._engine) as session, session.begin():
            session.merge(IdeaRow(**idea_values(idea)))

    def ideas(self) -> list[Idea]:
        with Session(self._engine) as session:
            rows = session.scalars(select(IdeaRow).order_by(IdeaRow.created_at.desc()))
            return [to_idea(row) for row in rows]

    def open_idea(self, symbol: str) -> Idea | None:
        query = select(IdeaRow).where(IdeaRow.symbol == symbol, IdeaRow.status == IDEA_NEW)
        with Session(self._engine) as session:
            row = session.scalars(query).first()
            return to_idea(row) if row else None

    def expire(self, idea: Idea) -> None:
        with Session(self._engine) as session, session.begin():
            session.execute(
                update(IdeaRow).where(IdeaRow.id == idea.id).values(status=IDEA_EXPIRED)
            )

    def save_screen(self, screen: Screen) -> None:
        with Session(self._engine) as session, session.begin():
            session.add(ScreenRecord(**screen_values(screen)))

    def latest_screen(self) -> Screen | None:
        query = select(ScreenRecord).order_by(ScreenRecord.seq.desc()).limit(1)
        with Session(self._engine) as session:
            row = session.scalars(query).first()
            try:
                return to_screen(row) if row else None
            except (TypeError, KeyError):  # stored by an older version with other fields
                return None

    def close(self) -> None:
        self._engine.dispose()
