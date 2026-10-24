from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import pytest

from fintrade.adapters.nse.bhavcopy import BhavcopyFetcher, bhavcopy_url
from fintrade.adapters.nse.raw_store import RawStore
from fintrade.services import bhavcopy_download
from fintrade.services.bhavcopy_download import DownloadJob, download_range
from tests.support.clock import FixedClock
from tests.support.http import make_zip, no_sleep

# Fri 2026-10-23, (weekend), Mon 2026-10-26, Tue 2026-10-27
START, END = date(2026, 10, 23), date(2026, 10, 27)
HOLIDAY = date(2026, 10, 26)


def _route(fail_days: frozenset[date] = frozenset()) -> httpx.MockTransport:
    urls = {bhavcopy_url(d): d for d in (START, HOLIDAY, END)}

    def handle(request: httpx.Request) -> httpx.Response:
        day = urls[str(request.url)]
        if day in fail_days:
            return httpx.Response(403)
        if day == HOLIDAY:
            return httpx.Response(404)
        return httpx.Response(200, content=make_zip())

    return httpx.MockTransport(handle)


def _job(
    root: Path, transport: httpx.MockTransport, *, retry_not_found: bool = False
) -> DownloadJob:
    return DownloadJob(
        fetcher=BhavcopyFetcher(httpx.Client(transport=transport), sleep=no_sleep),
        store=RawStore(root),
        clock=FixedClock(datetime(2026, 10, 27, 12, 0, tzinfo=UTC)),
        sleep=no_sleep,
        retry_not_found=retry_not_found,
    )


def test_first_run_downloads_and_marks_holiday(tmp_path: Path) -> None:
    summary = download_range(_job(tmp_path, _route()), START, END)
    assert summary.downloaded == [START, END]
    assert summary.not_found == [HOLIDAY]
    assert summary.skipped == summary.failed == []
    assert RawStore(tmp_path).path_for(END).exists()


def test_second_run_is_idempotent(tmp_path: Path) -> None:
    download_range(_job(tmp_path, _route()), START, END)
    summary = download_range(_job(tmp_path, _route()), START, END)
    assert summary.skipped == [START, HOLIDAY, END]
    assert summary.downloaded == []


def test_tampered_file_is_downloaded_again(tmp_path: Path) -> None:
    download_range(_job(tmp_path, _route()), START, END)
    RawStore(tmp_path).path_for(START).write_bytes(b"corrupted")
    summary = download_range(_job(tmp_path, _route()), START, END)
    assert summary.downloaded == [START]


def test_retry_not_found_refetches_holidays(tmp_path: Path) -> None:
    download_range(_job(tmp_path, _route()), START, END)
    summary = download_range(_job(tmp_path, _route(), retry_not_found=True), START, END)
    assert summary.not_found == [HOLIDAY]
    assert summary.skipped == [START, END]


def test_failed_day_is_counted_and_run_continues(tmp_path: Path) -> None:
    summary = download_range(_job(tmp_path, _route(frozenset({START}))), START, END)
    assert summary.failed == [START]
    assert summary.downloaded == [END]
    # Re-running retries the failed day.
    retry = download_range(_job(tmp_path, _route()), START, END)
    assert retry.downloaded == [START]


def _client_factory(transport: httpx.MockTransport) -> Callable[[], httpx.Client]:
    return lambda: httpx.Client(transport=transport)


def _args(root: Path, *extra: str) -> list[str]:
    return ["--start", "2026-10-23", "--end", "2026-10-27", "--root", str(root), *extra]


def test_main_returns_0_on_success(tmp_path: Path) -> None:
    code = bhavcopy_download.main(_args(tmp_path), _client_factory(_route()), no_sleep)
    assert code == 0
    assert RawStore(tmp_path).path_for(START).exists()


def test_main_returns_1_when_a_day_fails(tmp_path: Path) -> None:
    factory = _client_factory(_route(frozenset({END})))
    assert bhavcopy_download.main(_args(tmp_path, "--retry-not-found"), factory, no_sleep) == 1


def test_main_reads_sys_argv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "sys.argv",
        ["prog", "--start", "2026-10-27", "--end", "2026-10-27", "--root", str(tmp_path)],
    )
    assert bhavcopy_download.main(client_factory=_client_factory(_route()), sleep=no_sleep) == 0
