from ..client import AIClient
from typing import Dict, Any
import time
import os
from docflow.logging_lib import setup_logger
import requests

logger = setup_logger()

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class OpenAIProvider(AIClient):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        if api_key:
            os.environ['OPENAI_API_KEY'] = api_key
        self.model = model or 'gpt-3.5-turbo'
        if OpenAI:
            self.client = OpenAI()
        else:
            self.client = None

    def generate_text(self, prompt: str, **kwargs) -> Dict[str, Any]:
        t0 = time.time()
        if not self.client:
            return {'text': prompt, 'meta': {'provider': 'openai', 'model': self.model, 'latency': 0.0, 'error': 'openai library not available'}}
        try:
            resp = self.client.chat.completions.create(model=self.model, messages=[{'role': 'user', 'content': prompt}])
            text = resp.choices[0].message.content
            return {'text': text, 'meta': {'provider': 'openai', 'model': self.model, 'latency': time.time() - t0}}
        except Exception as e:
            return {'text': prompt, 'meta': {'provider': 'openai', 'model': self.model, 'latency': time.time() - t0, 'error': str(e)}}

    def generate_image(self, prompt: str, **kwargs) -> Dict[str, Any]:
        t0 = time.time()
        model = kwargs.get('model', 'dall-e-3')
        meta = {'provider': 'openai', 'model': model, 'latency': 0.0}

        if not self.client:
            meta['error'] = 'openai library not available'
            logger.error(meta['error'])
            return {'image_bytes': b'', 'meta': meta}

        try:
            response = self.client.images.generate(
                model=model,
                prompt=prompt,
                n=1,
                size=kwargs.get('size', '1024x1024'),
                response_format="url"
            )
            image_url = response.data[0].url

            try:
                image_response = requests.get(image_url)
                image_response.raise_for_status()
                image_bytes = image_response.content
                meta['latency'] = time.time() - t0
                return {'image_bytes': image_bytes, 'meta': meta}
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to download image from {image_url}: {e}")
                meta['error'] = f"Failed to download image: {e}"
                meta['latency'] = time.time() - t0
                return {'image_bytes': b'', 'meta': meta}

        except Exception as e:
            logger.error(f"Error generating image with OpenAI: {e}")
            meta['error'] = str(e)
            meta['latency'] = time.time() - t0
            return {'image_bytes': b'', 'meta': meta}

    def upload_file(self, path: str, mime_type: str | None = None) -> Dict[str, Any]:
        """Upload a file using openai.File.create when available. Returns the file object or raises."""
        if not self.client:
            raise NotImplementedError('openai library not available')
        
        try:
            with open(path, 'rb') as fh:
                file_obj = self.client.files.create(file=fh, purpose='assistants')
            ref = {'id': getattr(file_obj, 'id', None), 'raw': file_obj}
            logger.info({'event': 'upload_file', 'provider': 'openai', 'path': str(path), 'ref': ref})
            return ref
        except Exception as e:
            logger.error(f"Error uploading file to OpenAI: {e}")
            raise
