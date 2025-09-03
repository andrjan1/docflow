from typing import Dict, Any
import time
import json
import io
import matplotlib.pyplot as plt
from pathlib import Path
from ..results import ActionResult
from ..context import ExecutionContext
from ...runtime.prompt_builder import build_prompt_for_action
from ...kb.strategies import prepare_kb_for_action
from ...kb.loader import read_kb_texts
from ...logging_lib import setup_logger

logger = setup_logger(__name__)


class MockAIClient:
    def __init__(self, provider: str = 'mock', model: str = 'mock-1'):
        self.provider = provider
        self.model = model

    def generate_text(self, prompt: str) -> Dict[str, Any]:
        start = time.time()
        # mock: if prompt starts with JSON block, return it in text
        text = f"Echo: {prompt[:200]}"
        latency = time.time() - start
        return {'text': text, 'meta': {'provider': self.provider, 'model': self.model, 'latency': latency}}

    def generate_image(self, prompt: str) -> Dict[str, Any]:

        start = time.time()
        fig, ax = plt.subplots(figsize=(4, 2))
        ax.text(0.5, 0.5, prompt[:100], ha='center')
        ax.axis('off')
        bio = io.BytesIO()
        fig.savefig(bio, format='png')
        plt.close(fig)
        bio.seek(0)
        latency = time.time() - start
        return {'image_bytes': bio.getvalue(), 'meta': {'provider': self.provider, 'model': self.model, 'latency': latency}}


class GenerativeAction:
    def __init__(self, cfg: Dict[str, Any]):
        self.cfg = cfg or {}

    def _resolve_attachment_paths(self, attachments_cfg: Dict[str, Any]) -> list[Path]:
        paths = []
        raw = attachments_cfg.get('paths', []) if attachments_cfg else []
        for p in raw:
            pstr = str(p)
            # if pattern contains glob wildcard and is absolute, use glob.glob
            if any(ch in pstr for ch in ['*', '?', '[']):
                import glob

                matches = [Path(x) for x in glob.glob(pstr, recursive=True)]
                if matches:
                    paths.extend(matches)
                    continue
                # no matches -> explicit log; do not silently glob elsewhere
                logger.info({'event': 'attachments_glob_no_match', 'pattern': pstr})
                continue

            pth = Path(pstr)
            if pth.exists():
                paths.append(pth)
            else:
                logger.info({'event': 'attachment_path_missing', 'path': pstr})
        return paths

    def _get_client(self, ctx: Dict[str, Any]):
        # prefer ExecutionContext.ai_client if available
        if isinstance(ctx, dict):
            return None
        if getattr(ctx, 'ai_client', None):
            return ctx.ai_client
        return MockAIClient(provider=self.cfg.get('provider', 'mock'), model=self.cfg.get('model', 'mock-1'))

    def execute(self, ctx: ExecutionContext) -> ActionResult:
        # gather variables and build prompt
        vars_in = ctx.global_vars if ctx is not None else {}
        kb_text = prepare_kb_for_action(self.cfg, vars_in)
        prompt = build_prompt_for_action(self.cfg, vars_in, kb_text) or self.cfg.get('prompt', 'Hello')

        client = self._get_client(ctx)
        attachments_cfg = self.cfg.get('attachments') or {}
        attachment_paths = self._resolve_attachment_paths(attachments_cfg) if attachments_cfg else []
        remote_refs: list[Any] = []  # type: ignore[name-defined]
        if attachment_paths:
            logger.info({'event': 'attachments_found', 'count': len(attachment_paths)})
            if attachments_cfg.get('upload') and client and hasattr(client, 'upload_file'):
                mime = attachments_cfg.get('mime')
                for p in attachment_paths:
                    remote_refs.append(client.upload_file(str(p), mime_type=mime))
                logger.info({'event': 'attachments_uploaded', 'count': len(remote_refs)})
            if attachments_cfg.get('as_text'):
                texts = read_kb_texts([p for p in attachment_paths if p.is_file()])
                if texts:
                    prompt += '\n\n=== ATTACHED FILES TEXT ===\n\n' + '\n\n'.join(t for t in texts if t)
                    logger.info({'event': 'attachments_text_extracted', 'chars': sum(len(t) for t in texts)})

        provider_kwargs: Dict[str, Any] = {}
        if remote_refs:
            provider_kwargs['attachments'] = remote_refs

        retries = int(self.cfg.get('retries', 1) or 1)
        last_exc: Exception | None = None

        for attempt in range(1, retries + 1):
            try:
                start = time.time()
                mode = self.cfg.get('mode') or ('image' if self.cfg.get('returns') == 'image' else 'text')
                if mode == 'image':
                    logger.info({'event': 'generative_image_start', 'attempt': attempt})
                    out = client.generate_image(prompt, **provider_kwargs)
                    img_bytes = out.get('image_bytes')
                    if not img_bytes:
                        raise RuntimeError('Provider returned no image bytes')
                    latency = time.time() - start
                    assets_dir = Path(getattr(ctx, 'assets_dir', vars_in.get('_assets_dir', 'build/assets')))
                    assets_dir.mkdir(parents=True, exist_ok=True)
                    out_path = assets_dir / f"gen_image_{int(time.time()*1000)}.png"
                    out_path.write_bytes(img_bytes)
                    vars_out = dict(self.cfg.get('vars', {}) or {})
                    if self.cfg.get('export_path_var'):
                        vars_out[self.cfg.get('export_path_var')] = str(out_path)
                    meta = out.get('meta', {})
                    meta.update({'latency': latency, 'out_bytes': len(img_bytes), 'attempts': attempt, 'vars_emitted': len(vars_out)})
                    return ActionResult(kind='image', data=str(out_path), meta=meta, vars=vars_out)
                else:
                    logger.info({'event': 'generative_text_start', 'attempt': attempt})
                    out = client.generate_text(prompt, **provider_kwargs)
                    text = out.get('text') or ''
                    vars_out: Dict[str, Any] = {}
                    stripped = text.strip()
                    if stripped.startswith('{') or stripped.startswith('['):
                        try:
                            parsed = json.loads(stripped)
                            if isinstance(parsed, dict):
                                vars_out.update(parsed)
                        except Exception:
                            pass
                    vars_out.update(self.cfg.get('vars', {}) or {})
                    latency = time.time() - start
                    meta = out.get('meta', {})
                    meta.update({'latency': latency, 'out_bytes': len(text.encode('utf-8')), 'attempts': attempt, 'vars_emitted': len(vars_out)})
                    return ActionResult(kind='text', data=text, meta=meta, vars=vars_out)
            except Exception as e:  # store and retry
                last_exc = e
                logger.info({'event': 'generative_attempt_error', 'attempt': attempt, 'error': str(e)})
                if attempt < retries:
                    time.sleep(0.5 * attempt)
        # all attempts failed
        raise last_exc or RuntimeError('generative action failed')
