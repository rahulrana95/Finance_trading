"""Derive per-expiry lot sizes and trading windows from curated daily bars.

Writes a reference file the backtest uses for lot sizes and expiry dates.

Usage:
    uv run python -m fintrade.services.derive_contract_specs --start 2019-02-11 --end 2026-10-23
"""

import argparse
import json
import sys
from collections.abc import Sequence
from dataclasses import asdict
from datetime import date
from pathlib import Path

import structlog

from fintrade.adapters.parquet.daily_bars import DailyBarStore
from fintrade.core.contract_specs import ExpirySpec, LotSizeSource, derive_expiry_specs
from fintrade.core.errors import DataError
from fintrade.services.build_daily_bars import CURATED_ROOT
from fintrade.services.logging_setup import configure_logging

DEFAULT_OUTPUT = Path("data/reference/nifty_expiry_specs.json")

log = structlog.get_logger(__name__)


def write_specs(specs: Sequence[ExpirySpec], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [asdict(spec) | {"oi_gcd_consistent": spec.oi_gcd_consistent} for spec in specs]
    path.write_text(json.dumps(rows, indent=2, default=str) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--curated-root", type=Path, default=CURATED_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    configure_logging()
    bars = DailyBarStore(args.curated_root).read_range(args.start, args.end)
    try:
        specs = derive_expiry_specs(bars)
    except DataError as exc:
        log.exception("contract_specs_failed", error=str(exc))
        return 1
    write_specs(specs, args.output)
    lot_sizes = sorted({spec.lot_size for spec in specs if spec.lot_size is not None})
    log.info(
        "contract_specs_written",
        expiries=len(specs),
        lot_sizes=lot_sizes,
        unknown=sum(spec.source is LotSizeSource.UNKNOWN for spec in specs),
        gcd_inconsistent=sum(spec.oi_gcd_consistent is False for spec in specs),
        output=str(args.output),
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point; main() is tested directly
    sys.exit(main())
