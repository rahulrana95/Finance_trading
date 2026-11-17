"""Algo runs: list them, read one, and start one that finishes in the background."""

from dataclasses import asdict

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from steady.api.schemas import RunOut, RunRequest
from steady.constants import MSG_UNKNOWN_RUN, RUNS_PATH
from steady.domain import Run
from steady.services.algo import AlgoService, RunNotFoundError


def to_out(run: Run) -> RunOut:
    return RunOut.model_validate(asdict(run))


def runs_router(algo: AlgoService) -> APIRouter:
    router = APIRouter(prefix=RUNS_PATH, tags=["runs"])

    @router.get("")
    def list_runs() -> list[RunOut]:
        return [to_out(run) for run in algo.list_runs()]

    @router.get("/{run_id}")
    def get_run(run_id: str) -> RunOut:
        try:
            return to_out(algo.get_run(run_id))
        except RunNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"{MSG_UNKNOWN_RUN} {run_id}"
            ) from error

    @router.post("", status_code=status.HTTP_202_ACCEPTED)
    def start_run(tasks: BackgroundTasks, body: RunRequest | None = None) -> RunOut:
        run, created = algo.start((body or RunRequest()).kind)
        out = to_out(run)  # the answer shows it running; the work happens after the reply
        if created:
            tasks.add_task(algo.execute, run.id)
        return out

    return router
