# fintrade.adapters.nse

NSE public archive adapters. No API key needed.

| Module | Public API |
|---|---|
| `bhavcopy` | `bhavcopy_url(day)`, `format_for(day)` (old ≤ 2024-07-05, UDiFF from 2024-07-08), `BhavcopyFetcher(client, sleep).fetch(day)` → `Fetched` (content `None` = holiday), `validate_zip` |
| `bhavcopy_parser` | `parse_bhavcopy(content, day, symbol="NIFTY")` → `list[DailyContractBar]`; format detected from header; unknown header or bad row → `DataError` |
| `raw_store` | `RawStore(root)`: `save`, `mark_not_found`, `latest`, `is_intact`; append-only `manifest.jsonl` with SHA-256 |

Download a range (resumable; re-run to retry failures):

    uv --directory backend run python -m fintrade.services.bhavcopy_download --end 2026-10-23

Validate everything downloaded (writes `data/reports/bhavcopy_quality.json`, exit 1 on errors):

    uv --directory backend run python -m fintrade.services.bhavcopy_validate

Files land in `data/raw/nse_fo_bhavcopy/` (git-ignored).
