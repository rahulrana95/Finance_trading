"""File-based kill switch. Engaged when the flag file exists.

Fail closed: if the flag's state can't be determined (permission error, broken mount),
the switch is treated as ENGAGED, so no new orders go out.
"""

from pathlib import Path

import structlog

log = structlog.get_logger(__name__)


class FileKillSwitch:
    def __init__(self, flag_path: Path) -> None:
        self._flag = flag_path

    def is_engaged(self) -> bool:
        try:
            return self._flag.exists()
        except OSError:
            log.exception("kill_switch_unreadable", path=str(self._flag))
            return True

    def engage(self, reason: str) -> None:
        self._flag.parent.mkdir(parents=True, exist_ok=True)
        self._flag.write_text(reason + "\n", encoding="utf-8")
        log.critical("kill_switch_engaged", reason=reason)

    def release(self) -> None:
        self._flag.unlink(missing_ok=True)
        log.warning("kill_switch_released")
