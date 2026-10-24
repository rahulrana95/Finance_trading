"""Fake HTTP helpers: httpx MockTransport with scripted responses, plus zip builders."""

import io
import zipfile
from collections.abc import Callable, Sequence

import httpx

type Step = httpx.Response | Exception


def make_zip(members: dict[str, bytes] | None = None) -> bytes:
    """Build an in-memory zip. Default: one small CSV, like a real bhavcopy."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        for name, body in (members or {"bhav.csv": b"SYMBOL,CLOSE\nNIFTY,25000\n"}).items():
            archive.writestr(name, body)
    return buffer.getvalue()


class ScriptedTransport(httpx.MockTransport):
    """Returns (or raises) the given steps in order and records every requested URL."""

    def __init__(self, steps: Sequence[Step]) -> None:
        self.requests: list[httpx.Request] = []
        self._steps = list(steps)
        super().__init__(self._handle)

    def _handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        step = self._steps.pop(0)
        if isinstance(step, Exception):
            raise step
        return step


def routing_transport(route: Callable[[httpx.Request], httpx.Response]) -> httpx.MockTransport:
    return httpx.MockTransport(route)


def no_sleep(_seconds: float) -> None:
    """Injected in place of time.sleep so tests never wait."""
