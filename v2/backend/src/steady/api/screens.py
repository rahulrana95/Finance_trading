"""The market-fall screener: read the latest result, or start a new screen in the background."""

from dataclasses import asdict

from fastapi import APIRouter, BackgroundTasks, status

from steady.api.schemas import ScreenStateOut
from steady.constants import SCREENS_PATH
from steady.services.screener import ScreenerService, ScreenState


def to_out(state: ScreenState) -> ScreenStateOut:
    return ScreenStateOut.model_validate(asdict(state))


def screens_router(screener: ScreenerService) -> APIRouter:
    router = APIRouter(prefix=SCREENS_PATH, tags=["screens"])

    @router.get("/latest")
    def latest() -> ScreenStateOut:
        return to_out(screener.state())

    @router.post("", status_code=status.HTTP_202_ACCEPTED)
    def start(tasks: BackgroundTasks) -> ScreenStateOut:
        if screener.start():
            tasks.add_task(screener.execute)
        return to_out(screener.state())

    return router
