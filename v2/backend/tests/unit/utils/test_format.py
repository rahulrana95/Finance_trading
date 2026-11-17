import pytest

from steady.utils.format import inr


@pytest.mark.parametrize(
    ("value", "expected"),
    [(0, "0"), (999, "999"), (1000, "1,000"), (66666, "66,666"), (200000, "2,00,000"),
     (2000000, "20,00,000"), (123456789, "12,34,56,789"), (1125530.4, "11,25,530"),
     (-45000, "-45,000")],
)  # fmt: skip
def test_indian_grouping(value: float, expected: str):
    assert inr(value) == expected
