"""Serves the built single-page interface."""

from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response
from starlette.staticfiles import StaticFiles
from starlette.types import Scope

from steady.constants import INDEX_FILE, MSG_INTERFACE_NOT_BUILT


class SpaStaticFiles(StaticFiles):
    """Static files, plus: an address with no file extension loads the app itself.

    Starlette's StaticFiles does the file lookup and refuses paths outside the folder.
    """

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as error:
            is_page = error.status_code == status.HTTP_404_NOT_FOUND and not Path(path).suffix
            if not is_page:
                raise
            return await super().get_response(INDEX_FILE, scope)


def mount_interface(app: FastAPI, static_dir: Path | None) -> None:
    if static_dir is not None:
        app.mount("/", SpaStaticFiles(directory=static_dir, html=True), name="interface")
        return

    @app.get("/{path:path}", include_in_schema=False)
    def not_built(path: str) -> None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=MSG_INTERFACE_NOT_BUILT)
