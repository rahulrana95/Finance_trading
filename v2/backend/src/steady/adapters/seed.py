"""The starting stock list, shipped with the code until the database exists."""

import json
from importlib import resources

from steady import seeds
from steady.constants import SEED_FILE
from steady.core.scoring import FinYear
from steady.domain import Business, StockSeed


def load_seed_stocks() -> list[StockSeed]:
    rows = json.loads(resources.files(seeds).joinpath(SEED_FILE).read_text())
    return [
        StockSeed(
            **{k: v for k, v in row.items() if k not in ("financials", "business")},
            financials=tuple(FinYear(**year) for year in row["financials"]),
            business=Business(**row["business"]),
        )
        for row in rows
    ]
