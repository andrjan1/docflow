from abc import ABC, abstractmethod
from ..results import ActionResult
from ..context import ExecutionContext


class Action(ABC):
    id: str

    @abstractmethod
    def execute(self, ctx: ExecutionContext) -> ActionResult:
        raise NotImplementedError()
