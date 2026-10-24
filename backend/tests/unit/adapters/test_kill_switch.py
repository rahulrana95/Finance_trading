from pathlib import Path

import pytest

from fintrade.adapters.kill_switch import FileKillSwitch
from fintrade.ports.kill_switch import KillSwitch


def test_engage_and_release(tmp_path: Path) -> None:
    switch: KillSwitch = FileKillSwitch(tmp_path / "flags" / "kill")
    assert switch.is_engaged() is False
    assert isinstance(switch, FileKillSwitch)
    switch.engage("owner pressed kill switch")
    assert switch.is_engaged() is True
    assert (tmp_path / "flags" / "kill").read_text() == "owner pressed kill switch\n"
    switch.release()
    assert switch.is_engaged() is False
    switch.release()  # releasing twice is harmless


def test_unreadable_flag_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def broken(_self: Path) -> bool:
        raise PermissionError("cannot stat flag")

    monkeypatch.setattr(Path, "exists", broken)
    assert FileKillSwitch(tmp_path / "kill").is_engaged() is True
