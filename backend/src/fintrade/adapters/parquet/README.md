# fintrade.adapters.parquet

| Module | Public API |
|---|---|
| `daily_bars` | `DailyBarStore(root)`: `write_day(day, bars, source_sha256)`, `read_day`, `read_range(start, end)`, `source_sha256(day)`; `SCHEMA` (prices as decimal128, never float) |

Build curated bars from the raw bhavcopy store (fail closed: days with errors are not written):

    uv --directory backend run python -m fintrade.services.build_daily_bars

Output: `data/curated/nifty_daily_bars/<year>/<yyyy-mm-dd>.parquet` (git-ignored).
