"""Suite-wide pytest rules (TESTING.md section 1)."""

import pytest

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
