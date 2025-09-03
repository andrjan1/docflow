import os
from ..ai.client import AIClient
from ..ai.providers.mock import MockProvider
from ..logging_lib import setup_logger

logger = setup_logger(__name__)

try:  # optional imports
    from ..ai.providers.openai import OpenAIProvider  # type: ignore
except Exception:  # pragma: no cover
    OpenAIProvider = None  # type: ignore

try:
    from ..ai.providers.gemini import GeminiProvider  # type: ignore
except Exception:  # pragma: no cover
    GeminiProvider = None  # type: ignore


def make_ai_client(cfg: dict) -> AIClient:
    kind = cfg.get('provider', 'mock')
    api_key_env = cfg.get('api_key_envvar')
    api_key = os.environ.get(api_key_env) if api_key_env else None
    model = cfg.get('model')
    logger.info({'event': 'ai_client_make_start', 'provider': kind, 'model': model})
    if kind == 'mock':
        logger.info({'event': 'ai_client_selected', 'provider': 'mock'})
        return MockProvider(model=model)
    if kind == 'openai':
        if OpenAIProvider is None:
            raise RuntimeError('OpenAI provider requested but dependencies not installed')
        logger.info({'event': 'ai_client_selected', 'provider': 'openai'})
        return OpenAIProvider(api_key=api_key, model=model)  # type: ignore
    if kind == 'gemini':
        if GeminiProvider is None:
            raise RuntimeError('Gemini provider requested but dependencies not installed')
        logger.info({'event': 'ai_client_selected', 'provider': 'gemini'})
        return GeminiProvider(api_key=api_key, model=model)  # type: ignore
    raise ValueError(f"Unknown AI provider '{kind}'")
