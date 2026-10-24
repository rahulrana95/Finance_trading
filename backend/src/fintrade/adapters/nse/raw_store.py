"""Local raw-file store with an append-only manifest and SHA-256 checksums.

Layout:
    <root>/<year>/<yyyy-mm-dd>.csv.zip
    <root>/manifest.jsonl   one JSON record per download attempt, never rewritten
"""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime
from enum import StrEnum
from pathlib import Path

from fintrade.core.errors import DataError

MANIFEST_NAME = "manifest.jsonl"
FILE_SUFFIX = ".csv.zip"


class RecordStatus(StrEnum):
    OK = "ok"
    NOT_FOUND = "not_found"


@dataclass(frozen=True, slots=True)
class ManifestRecord:
    day: str
    status: RecordStatus
    url: str
    fetched_at: str
    sha256: str | None = None
    size_bytes: int | None = None


def sha256_hex(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class RawStore:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._manifest = root / MANIFEST_NAME

    def path_for(self, day: date) -> Path:
        return self._root / str(day.year) / f"{day.isoformat()}{FILE_SUFFIX}"

    def save(self, day: date, url: str, content: bytes, fetched_at: datetime) -> ManifestRecord:
        """Write the file (atomically) and append an OK record."""
        target = self.path_for(day)
        target.parent.mkdir(parents=True, exist_ok=True)
        partial = target.with_suffix(target.suffix + ".part")
        partial.write_bytes(content)
        partial.replace(target)
        record = ManifestRecord(
            day=day.isoformat(),
            status=RecordStatus.OK,
            url=url,
            fetched_at=fetched_at.isoformat(),
            sha256=sha256_hex(content),
            size_bytes=len(content),
        )
        self._append(record)
        return record

    def mark_not_found(self, day: date, url: str, fetched_at: datetime) -> ManifestRecord:
        record = ManifestRecord(
            day=day.isoformat(),
            status=RecordStatus.NOT_FOUND,
            url=url,
            fetched_at=fetched_at.isoformat(),
        )
        self._append(record)
        return record

    def latest(self) -> dict[str, ManifestRecord]:
        """Latest manifest record per day. The last line for a day wins."""
        if not self._manifest.exists():
            return {}
        latest: dict[str, ManifestRecord] = {}
        for line_number, line in enumerate(self._manifest.read_text("utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                record = ManifestRecord(**{**raw, "status": RecordStatus(raw["status"])})
            except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
                raise DataError(f"bad manifest line {line_number}: {line!r}") from exc
            latest[record.day] = record
        return latest

    def load(self, record: ManifestRecord) -> bytes:
        """Read a stored file, refusing it if missing or if its checksum changed."""
        if record.status is not RecordStatus.OK:
            raise DataError(f"no stored file for {record.day} (status {record.status})")
        path = self.path_for(date.fromisoformat(record.day))
        if not path.exists():
            raise DataError(f"stored file missing: {path}")
        content = path.read_bytes()
        if sha256_hex(content) != record.sha256:
            raise DataError(f"checksum mismatch: {path}")
        return content

    def is_intact(self, record: ManifestRecord) -> bool:
        """True if the stored file exists and still matches its recorded checksum."""
        if record.status is not RecordStatus.OK:
            return False
        path = self.path_for(date.fromisoformat(record.day))
        return path.exists() and sha256_hex(path.read_bytes()) == record.sha256

    def _append(self, record: ManifestRecord) -> None:
        self._root.mkdir(parents=True, exist_ok=True)
        with self._manifest.open("a", encoding="utf-8") as manifest:
            manifest.write(json.dumps(asdict(record), sort_keys=True) + "\n")
