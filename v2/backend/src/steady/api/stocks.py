"""Read-only stock table routes."""

from dataclasses import asdict

from fastapi import APIRouter, HTTPException, status

from steady.api.schemas import StockOut
from steady.constants import MSG_UNKNOWN_STOCK, STOCKS_PATH
from steady.services.stocks import StockNotFoundError, StockService, StockView


def to_out(view: StockView) -> StockOut:
    seed = asdict(view.seed)
    fields = {k: v for k, v in asdict(view).items() if k != "seed"}
    scores = {k: fields.pop(k) for k in ("stability", "financial", "data_quality", "evidence")}
    return StockOut.model_validate({**seed, **fields, "scores": scores})


def stocks_router(service: StockService) -> APIRouter:
    router = APIRouter(prefix=STOCKS_PATH, tags=["stocks"])

    @router.get("")
    def list_stocks() -> list[StockOut]:
        return [to_out(view) for view in service.list_stocks()]

    @router.get("/{symbol}")
    def get_stock(symbol: str) -> StockOut:
        try:
            return to_out(service.get_stock(symbol))
        except StockNotFoundError as error:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"{MSG_UNKNOWN_STOCK} {symbol}"
            ) from error

    return router
