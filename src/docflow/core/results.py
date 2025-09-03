from pydantic import BaseModel
from typing import Literal, Any
from pathlib import Path


class ActionResult(BaseModel):
    kind: Literal['text', 'image', 'bytes']
    data: str | bytes | Path
    meta: dict[str, Any] = {}
    vars: dict[str, Any] = {}
