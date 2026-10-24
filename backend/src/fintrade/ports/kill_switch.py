"""Kill switch port. Every agent checks it before sending any order (AGENTS.md section 2)."""

from typing import Protocol


class KillSwitch(Protocol):
    def is_engaged(self) -> bool:
        """True when new orders must stop. Must return True if the state is unknown."""
        ...
