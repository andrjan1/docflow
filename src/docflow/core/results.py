from pydantic import BaseModel
from typing import Literal, Any, Union, List
from pathlib import Path


class ActionResult(BaseModel):
    kind: Union[Literal['text', 'image', 'bytes', 'vars'], List[Literal['text', 'image', 'bytes', 'vars']]]
    data: Union[str, bytes, Path, dict, List[Any]]
    meta: dict[str, Any] = {}
    vars: dict[str, Any] = {}

class MultipleActionResult(BaseModel):
    """Result for actions that return multiple outputs"""
    results: List[ActionResult]
    meta: dict[str, Any] = {}
    vars: dict[str, Any] = {}
