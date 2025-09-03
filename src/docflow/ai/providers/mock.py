from ..client import AIClient
from typing import Dict, Any
import time
from docflow.logging_lib import setup_logger

logger = setup_logger()


class MockProvider(AIClient):
    def __init__(self, model: str = 'mock-1'):
        self.model = model

    def generate_text(self, prompt: str, **kwargs) -> Dict[str, Any]:
        t0 = time.time()
        # deterministic echo with small transform
        out = f"MOCK_TEXT:{prompt[:100]}"
        return {'text': out, 'meta': {'provider': 'mock', 'model': self.model, 'latency': time.time() - t0}}

    def generate_image(self, prompt: str, **kwargs) -> Dict[str, Any]:
        # return a deterministic valid 1x1 PNG (white)
        t0 = time.time()
        png_1x1_b64 = 'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8Xw8AAmEBg6ou2hkAAAAASUVORK5CYII='
        import base64
        b = base64.b64decode(png_1x1_b64)
        return {'image_bytes': b, 'meta': {'provider': 'mock', 'model': self.model, 'latency': time.time() - t0, 'placeholder': True}}

    def upload_file(self, path: str, mime_type: str | None = None) -> Dict[str, str]:
        # deterministic mock reference for tests and local usage
        ref = {'id': f'mock://{path}', 'mime_type': mime_type or 'application/octet-stream'}
        logger.info({'event': 'upload_file', 'provider': 'mock', 'path': str(path), 'ref': ref})
        return ref
