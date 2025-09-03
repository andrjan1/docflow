from ..client import AIClient
from typing import Dict, Any
import time
import os
from docflow.logging_lib import setup_logger

logger = setup_logger(__name__)

try:  # optional dependency
    import google.generativeai as genai  # type: ignore
except ImportError:  # pragma: no cover
    genai = None  # type: ignore


class GeminiProvider(AIClient):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        if genai is None:
            raise RuntimeError('google-generativeai package not installed')
        if api_key:
            os.environ['GOOGLE_API_KEY'] = api_key
            genai.configure(api_key=api_key)  # type: ignore
        self.model = model or 'gemini-1'
        logger.info({'event': 'gemini_init', 'model': self.model})

    def generate_text(self, prompt: str, **kwargs) -> Dict[str, Any]:
        t0 = time.time()
        if genai is None:  # defensive; constructor prevents this
            raise RuntimeError('Gemini SDK unavailable')
        logger.info({'event': 'gemini_generate_text_start', 'model': self.model, 'chars': len(prompt)})
        try:
            if not hasattr(genai, 'GenerativeModel'):
                raise RuntimeError('GenerativeModel API not present in google-generativeai package')
            gmodel = genai.GenerativeModel(self.model)  # type: ignore
            resp = gmodel.generate_content(prompt)  # modern SDK call
            # extract text
            if hasattr(resp, 'text') and resp.text:
                text = resp.text
            elif hasattr(resp, 'candidates') and resp.candidates:  # concatenate candidate parts
                parts = []
                for c in resp.candidates:
                    content = getattr(c, 'content', None)
                    if content and getattr(content, 'parts', None):
                        for part in content.parts:
                            val = getattr(part, 'text', None)
                            if val:
                                parts.append(val)
                text = '\n'.join(parts) if parts else ''
            else:
                text = str(resp)
            latency = time.time() - t0
            logger.info({'event': 'gemini_generate_text_end', 'model': self.model, 'latency': latency, 'out_chars': len(text)})
            return {'text': text, 'meta': {'provider': 'gemini', 'model': self.model, 'latency': latency}}
        except Exception as e:  # no fallback, just classify error
            latency = time.time() - t0
            msg = str(e)
            structured = {'event': 'gemini_generate_text_error', 'model': self.model, 'latency': latency, 'error': msg}
            # detect invalid API key to raise cleaner actionable error
            if 'API key not valid' in msg or 'API_KEY_INVALID' in msg:
                structured['category'] = 'auth'
                structured['auth_error'] = 'invalid_api_key'
                logger.info(structured)
                try:
                    from docflow.errors import ActionError
                except Exception:  # pragma: no cover - defensive
                    raise RuntimeError('Gemini API key invalid. Provide a valid GEMINI_API_KEY.') from e
                raise ActionError('Gemini API key invalid. Set a valid GEMINI_API_KEY environment variable or update config.ai.api_key.') from e
            logger.info(structured)
            raise

    def generate_image(self, prompt: str, **kwargs) -> Dict[str, Any]:
        t0 = time.time()
        if genai is None:
            raise RuntimeError('Gemini SDK unavailable')
        model = kwargs.get('model') or self.model
        logger.info({'event': 'gemini_generate_image_start', 'model': model, 'chars': len(prompt)})
        if not hasattr(genai, 'GenerativeModel'):
            raise RuntimeError('GenerativeModel API missing in installed gemini SDK')
        gmodel = genai.GenerativeModel(model)  # type: ignore
        # try modern generate_image / generate_images / generate_content order
        call_resp = None
        for attr in ('generate_image', 'generate_images', 'generate_content'):
            if hasattr(gmodel, attr):
                fn = getattr(gmodel, attr)
                call_resp = fn(prompt=prompt) if 'prompt' in fn.__code__.co_varnames else fn(prompt)  # type: ignore
                break
        if call_resp is None:
            raise RuntimeError('No usable image generation method found')
        # naive extraction; expect SDK to expose .images[0].base64_data or similar
        b64_data = None
        images = getattr(call_resp, 'images', None)
        if images:
            first = images[0]
            b64_data = getattr(first, 'base64_data', None) or getattr(first, 'data', None)
        if b64_data is None and hasattr(call_resp, 'generated_images'):
            gi = getattr(call_resp, 'generated_images')
            if gi:
                b64_data = getattr(gi[0], 'base64_data', None)
        if not isinstance(b64_data, str):
            raise RuntimeError('Gemini response missing base64 image data')
        import base64 as _b64
        img_bytes = _b64.b64decode(b64_data)
        latency = time.time() - t0
        logger.info({'event': 'gemini_generate_image_end', 'model': model, 'latency': latency, 'bytes': len(img_bytes)})
        return {'image_bytes': img_bytes, 'meta': {'provider': 'gemini', 'model': model, 'latency': latency}}

    def upload_file(self, path: str, mime_type: str | None = None) -> Any:
        if genai is None or not hasattr(genai, 'upload_file'):
            raise NotImplementedError('Gemini upload not available')
        logger.info({'event': 'gemini_upload_start', 'path': path})
        remote = genai.upload_file(path=str(path), mime_type=mime_type or 'application/octet-stream')  # type: ignore
        logger.info({'event': 'gemini_upload_end', 'path': path, 'remote': str(remote)})
        return remote
