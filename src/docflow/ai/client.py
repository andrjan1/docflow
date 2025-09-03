from abc import ABC, abstractmethod
from typing import Any, Dict


class AIClient(ABC):
    @abstractmethod
    def generate_text(self, prompt: str, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError()

    @abstractmethod
    def generate_image(self, prompt: str, **kwargs) -> Dict[str, Any]:
        raise NotImplementedError()

    def upload_file(self, path: str, mime_type: str | None = None) -> Any:
        """Optional: upload file to provider and return a provider-specific reference.

        Default implementation raises NotImplementedError so providers implement it when available.
        """
        raise NotImplementedError()
