"""Response shapes for the API."""

from datetime import datetime

from pydantic import BaseModel


class Health(BaseModel):
    status: str
    service: str
    version: str
    time: datetime
