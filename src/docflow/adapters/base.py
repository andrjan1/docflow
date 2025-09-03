from abc import ABC, abstractmethod
from typing import Dict, Any, List
from pathlib import Path


class DocumentAdapter(ABC):
    def __init__(self, path: Path):
        self.path = Path(path)

    @abstractmethod
    def load(self):
        raise NotImplementedError()

    @abstractmethod
    def list_placeholders(self) -> List[str]:
        raise NotImplementedError()

    @abstractmethod
    def apply(self, mapping: Dict[str, Any], global_vars: Dict[str, Any]):
        raise NotImplementedError()

    @abstractmethod
    def save(self, out_path: Path):
        raise NotImplementedError()
