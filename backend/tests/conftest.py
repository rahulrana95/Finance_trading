"""Suite-wide pytest rules (TESTING.md section 1)."""

import os

import pytest
from hypothesis import HealthCheck, settings

# Hypothesis profiles: "ci" is deterministic so failures reproduce exactly.
settings.register_profile(
    "ci",
    derandomize=True,
    max_examples=200,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.register_profile("dev", max_examples=50)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "ci"))

SKIPPED_TESTS_EXIT_CODE = 3


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    """Fail the run if any test was skipped: skips hide untested behavior."""
    reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if reporter is None:
        return
    skipped = reporter.stats.get("skipped", [])
    if skipped and exitstatus == pytest.ExitCode.OK:
        reporter.write_line(f"FAILED: {len(skipped)} skipped test(s). Skips are not allowed.")
        session.exitstatus = SKIPPED_TESTS_EXIT_CODE
