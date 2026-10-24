"""Download NSE F&O bhavcopy (daily, all contracts) from the public NSE archive.

Two file formats exist:
- old format, up to and including 2024-07-05
- UDiFF format, from 2024-07-08 onwards
"""

import io
import zipfile
import zlib
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

import httpx
from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from fintrade.core.errors import DataError

OLD_FORMAT_LAST_DAY = date(2024, 7, 5)
NIFTY_WEEKLY_OPTIONS_START = date(2019, 2, 11)

_ARCHIVE = "https://nsearchives.nseindia.com/content"
_OLD_URL = _ARCHIVE + "/historical/DERIVATIVES/{year}/{mon}/fo{day:02d}{mon}{year}bhav.csv.zip"
_UDIFF_URL = _ARCHIVE + "/fo/BhavCopy_NSE_FO_0_0_0_{ymd}_F_0000.csv.zip"
_MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")

REQUEST_HEADERS: dict[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Referer": "https://www.nseindia.com/",
    "Accept": "application/zip,*/*",
}
REQUEST_TIMEOUT_SECONDS = 30.0
MAX_ATTEMPTS = 3
RETRY_WAIT_MIN_SECONDS = 2.0
RETRY_WAIT_MAX_SECONDS = 16.0

HTTP_OK = 200
HTTP_NOT_FOUND = 404
HTTP_TOO_MANY_REQUESTS = 429
HTTP_SERVER_ERROR = 500


class BhavcopyFormat(StrEnum):
    OLD = "old"
    UDIFF = "udiff"


def format_for(day: date) -> BhavcopyFormat:
    return BhavcopyFormat.OLD if day <= OLD_FORMAT_LAST_DAY else BhavcopyFormat.UDIFF


def bhavcopy_url(day: date) -> str:
    if format_for(day) is BhavcopyFormat.OLD:
        return _OLD_URL.format(year=day.year, mon=_MONTHS[day.month - 1], day=day.day)
    return _UDIFF_URL.format(ymd=day.strftime("%Y%m%d"))


@dataclass(frozen=True, slots=True)
class Fetched:
    day: date
    url: str
    content: bytes | None  # None means NSE has no file for that day (holiday)


class RetryableHttpError(DataError):
    """Rate limit or server error: safe to retry a read-only GET."""


def validate_zip(content: bytes, url: str) -> None:
    """Reject HTML error pages, truncated or corrupt archives, and unexpected contents."""
    buffer = io.BytesIO(content)
    if not zipfile.is_zipfile(buffer):
        raise DataError(f"not a zip archive: {url}")
    try:
        with zipfile.ZipFile(buffer) as archive:
            names = archive.namelist()
            bad_member = archive.testzip()
    except (zipfile.BadZipFile, zlib.error, EOFError) as exc:
        raise DataError(f"corrupt zip: {url}") from exc
    if bad_member is not None:
        raise DataError(f"corrupt member {bad_member}: {url}")
    if len(names) != 1 or not names[0].lower().endswith(".csv"):
        raise DataError(f"expected one CSV in zip, got {names}: {url}")


class BhavcopyFetcher:
    """Fetches one day's file. Read-only GETs, so limited retries are safe."""

    def __init__(self, client: httpx.Client, sleep: Callable[[float], None]) -> None:
        self._client = client
        self._retrying = Retrying(
            stop=stop_after_attempt(MAX_ATTEMPTS),
            wait=wait_exponential(min=RETRY_WAIT_MIN_SECONDS, max=RETRY_WAIT_MAX_SECONDS),
            retry=retry_if_exception_type((httpx.TransportError, RetryableHttpError)),
            sleep=sleep,
            reraise=True,
        )

    def fetch(self, day: date) -> Fetched:
        url = bhavcopy_url(day)
        try:
            response = self._retrying(self._get, url)
        except httpx.TransportError as exc:
            raise DataError(f"network error after {MAX_ATTEMPTS} attempts: {url}") from exc
        if response.status_code == HTTP_NOT_FOUND:
            return Fetched(day=day, url=url, content=None)
        validate_zip(response.content, url)
        return Fetched(day=day, url=url, content=response.content)

    def _get(self, url: str) -> httpx.Response:
        response = self._client.get(url, headers=REQUEST_HEADERS, timeout=REQUEST_TIMEOUT_SECONDS)
        status = response.status_code
        if status == HTTP_TOO_MANY_REQUESTS or status >= HTTP_SERVER_ERROR:
            raise RetryableHttpError(f"HTTP {status}: {url}")
        if status not in {HTTP_OK, HTTP_NOT_FOUND}:
            raise DataError(f"unexpected HTTP {status}: {url}")
        return response
