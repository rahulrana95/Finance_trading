from hypothesis import given, settings
from hypothesis import strategies as st


def test_ci_profile_is_deterministic() -> None:
    assert settings().derandomize is True


@given(st.integers())
def test_property_tests_run(value: int) -> None:
    assert value - value == 0
