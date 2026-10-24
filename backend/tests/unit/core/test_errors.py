import pytest

from fintrade.core.errors import (
    BrokerError,
    ConfigError,
    DataError,
    FintradeError,
    InvalidInputError,
    RuleViolation,
    StaleDataError,
)


@pytest.mark.parametrize(
    "error_type",
    [InvalidInputError, ConfigError, DataError, StaleDataError, BrokerError],
)
def test_every_error_is_a_fintrade_error(error_type: type[FintradeError]) -> None:
    assert issubclass(error_type, FintradeError)


def test_stale_data_is_a_data_error() -> None:
    with pytest.raises(DataError):
        raise StaleDataError("tick 6 min old")


def test_rule_violation_carries_code_and_detail() -> None:
    err = RuleViolation("DELTA_TOO_HIGH", "0.13 > 0.12")
    assert err.code == "DELTA_TOO_HIGH"
    assert err.detail == "0.13 > 0.12"
    assert str(err) == "DELTA_TOO_HIGH: 0.13 > 0.12"
    assert isinstance(err, FintradeError)
