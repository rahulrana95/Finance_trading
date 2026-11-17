from datetime import UTC

from steady.clock import utc_now


def test_utc_now_is_timezone_aware():
    assert utc_now().tzinfo is UTC
