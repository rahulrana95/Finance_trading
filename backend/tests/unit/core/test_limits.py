"""The hard limits in code must match the locked AGENTS.md table, value for value."""

import dataclasses
import re
from datetime import time
from decimal import Decimal
from pathlib import Path

import pytest

from fintrade.core.limits import HARD_LIMITS, HardLimits

AGENTS_MD = Path(__file__).resolve().parents[4] / "AGENTS.md"


def _agents_table() -> dict[str, str]:
    """Parse the AGENTS.md section 1 table into {limit name: value text}."""
    text = AGENTS_MD.read_text(encoding="utf-8")
    section = text.split("## 1. Hard trading limits", 1)[1].split("\n## ", 1)[0]
    rows = re.findall(r"^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|$", section, flags=re.MULTILINE)
    return {name: value for name, value in rows if name not in {"Limit", "---"}}


def _number(text: str) -> Decimal:
    match = re.search(r"\d+(?:\.\d+)?", text)
    assert match is not None, f"no number in {text!r}"
    return Decimal(match.group())


@pytest.fixture(scope="module")
def table() -> dict[str, str]:
    return _agents_table()


def test_table_parsed(table: dict[str, str]) -> None:
    assert len(table) == 15


def test_underlying(table: dict[str, str]) -> None:
    assert "Nifty 50" in table["Underlying"]
    assert HARD_LIMITS.underlying == "NIFTY"


@pytest.mark.parametrize(
    ("row", "field"),
    [
        ("Short option delta", "max_short_delta"),
        ("Expiry for new entries", "min_days_to_expiry_at_entry"),
        ("Weekly loss", "max_weekly_loss_pct"),
        ("Monthly drawdown", "max_monthly_drawdown_pct"),
        ("Yearly drawdown", "max_yearly_drawdown_pct"),
        ("Open positions", "max_open_positions"),
        ("New positions per day", "max_new_positions_per_day"),
        ("Margin used", "max_margin_used_pct"),
        ("Adjustments per position", "max_adjustments_per_position"),
    ],
)
def test_numeric_limit_matches_agents_md(table: dict[str, str], row: str, field: str) -> None:
    assert Decimal(getattr(HARD_LIMITS, field)) == _number(table[row])


def test_exit_cutoff_matches_agents_md(table: dict[str, str]) -> None:
    assert "15:00" in table["Hold into expiry day"]
    assert HARD_LIMITS.exit_cutoff_day_before_expiry == time(15, 0)


def test_structure_rules_present(table: dict[str, str]) -> None:
    assert "Defined risk only" in table["Structure"]
    assert "Never" in table["Naked short options"]


def test_golden_values() -> None:
    # Literal expected values on purpose (ENGINEERING.md section 4).
    assert HARD_LIMITS.max_short_delta == Decimal("0.12")
    assert HARD_LIMITS.max_weekly_loss_pct == Decimal(1)
    assert HARD_LIMITS.max_monthly_drawdown_pct == Decimal(3)
    assert HARD_LIMITS.max_yearly_drawdown_pct == Decimal(5)
    assert HARD_LIMITS.max_margin_used_pct == Decimal(60)


def test_limits_are_immutable() -> None:
    with pytest.raises(dataclasses.FrozenInstanceError):
        HARD_LIMITS.max_short_delta = Decimal("0.20")  # type: ignore[misc]
    assert isinstance(HARD_LIMITS, HardLimits)
