import io
import zipfile

import pytest

from fintrade.adapters.nse.bhavcopy import validate_zip
from fintrade.core.errors import DataError
from tests.support.http import make_zip

URL = "https://example.test/file.zip"


def test_valid_single_csv_zip_passes() -> None:
    validate_zip(make_zip(), URL)


def test_html_error_page_rejected() -> None:
    with pytest.raises(DataError, match="not a zip"):
        validate_zip(b"<html>Access Denied</html>", URL)


def test_truncated_zip_rejected() -> None:
    content = make_zip()
    with pytest.raises(DataError):
        validate_zip(content[: len(content) // 2] + content[-22:], URL)


def _corrupted(compression: int) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=compression) as archive:
        archive.writestr("bhav.csv", b"A" * 1000)
    content = bytearray(buffer.getvalue())
    data_start = 30 + len("bhav.csv")  # local header size + file name
    content[data_start + 2] ^= 0xFF  # flip bits inside the member data
    return bytes(content)


def test_corrupt_stored_member_rejected() -> None:
    with pytest.raises(DataError, match=r"corrupt member bhav\.csv"):
        validate_zip(_corrupted(zipfile.ZIP_STORED), URL)


def test_corrupt_compressed_member_rejected() -> None:
    # Regression: zlib.error used to escape as a crash instead of a DataError.
    with pytest.raises(DataError, match="corrupt zip"):
        validate_zip(_corrupted(zipfile.ZIP_DEFLATED), URL)


@pytest.mark.parametrize(
    "members",
    [
        {"a.csv": b"x", "b.csv": b"y"},
        {"readme.txt": b"x"},
    ],
)
def test_unexpected_contents_rejected(members: dict[str, bytes]) -> None:
    with pytest.raises(DataError, match="expected one CSV"):
        validate_zip(make_zip(members), URL)


def test_empty_zip_rejected() -> None:
    buffer = io.BytesIO()
    zipfile.ZipFile(buffer, "w").close()
    with pytest.raises(DataError, match="expected one CSV"):
        validate_zip(buffer.getvalue(), URL)
